"""
GENOVEX Phase 7: Deterministic Clinical Rule Engine - Predicate Evaluator
Formalizes three-valued logic (TRUE, FALSE, INDETERMINATE), compound boolean
combinators (all_of, any_of, none_of), strict recursion depth limits (<= 3),
and the four clinical rule evaluation states (TRIGGERED, EXPLICIT_NON_TRIGGER,
INDETERMINATE, NOT_APPLICABLE).
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Union


class PredicateEvaluationState(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    INDETERMINATE = "INDETERMINATE"


class RuleEvaluationState(str, Enum):
    TRIGGERED = "TRIGGERED"
    EXPLICIT_NON_TRIGGER = "EXPLICIT_NON_TRIGGER"
    INDETERMINATE = "INDETERMINATE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


MAX_PREDICATE_DEPTH = 3


class PredicateEvaluator:
    """
    Pure algorithmic evaluator for deterministic clinical predicates.
    Supports atomic operators (equals, in, contains, greater_than, less_than)
    and compound trees (all_of, any_of, none_of) with three-valued logic.
    """

    @classmethod
    def validate_predicate_structure(cls, trigger: Dict[str, Any], depth: int = 1) -> None:
        """
        Validates predicate schema:
        1. Max recursion depth <= 3.
        2. Compound combinators (all_of, any_of, none_of) must have non-empty conditions.
        3. Atomic leaves must have question_key and valid operator.
        Raises ValueError on violation.
        """
        if depth > MAX_PREDICATE_DEPTH:
            raise ValueError(
                f"Predicate nesting depth exceeds maximum allowed limit of {MAX_PREDICATE_DEPTH} levels."
            )

        if not isinstance(trigger, dict):
            raise ValueError(f"Predicate must be a JSON object, got: {type(trigger).__name__}")

        combinator = trigger.get("combinator")
        if combinator:
            comb_lower = combinator.lower()
            if comb_lower not in ["all_of", "any_of", "none_of"]:
                raise ValueError(f"Unsupported combinator '{combinator}'. Must be all_of, any_of, or none_of.")
            
            conditions = trigger.get("conditions")
            if not isinstance(conditions, list) or len(conditions) == 0:
                raise ValueError(f"Compound predicate '{combinator}' must contain a non-empty list of conditions.")

            for child in conditions:
                cls.validate_predicate_structure(child, depth=depth + 1)
        else:
            # Atomic predicate
            question_key = trigger.get("question_key")
            if not question_key:
                raise ValueError("Atomic predicate must declare 'question_key'.")
            operator = trigger.get("operator", "equals").lower()
            valid_operators = ["equals", "in", "contains", "greater_than", "less_than"]
            if operator not in valid_operators:
                raise ValueError(f"Unsupported operator '{operator}'. Must be one of {valid_operators}.")

    @classmethod
    def extract_response_attributes(cls, resp: Any) -> Tuple[Optional[Any], bool, bool, bool]:
        """
        Extracts (concrete_value, is_unsure, is_prefer_not_to_say, is_pathway_active)
        from AssessmentResponse or dictionary mock fixture.
        """
        if resp is None:
            return None, False, False, True

        is_unsure = False
        is_prefer_not_to_say = False
        is_active = True
        val = None

        if isinstance(resp, dict):
            is_unsure = bool(resp.get("is_unsure", False))
            is_prefer_not_to_say = bool(resp.get("is_prefer_not_to_say", False))
            active_val = resp.get("conditional_pathway_active")
            is_active = True if active_val is None else bool(active_val)
            val = resp.get("answer_value")
            if val is None:
                val = resp.get("value") or resp.get("response_value_json")
        else:
            # SQLAlchemy model or class instance
            is_unsure = bool(getattr(resp, "is_unsure", False))
            is_prefer_not_to_say = bool(getattr(resp, "is_prefer_not_to_say", False))
            active_val = getattr(resp, "conditional_pathway_active", True)
            is_active = True if active_val is None else bool(active_val)
            if hasattr(resp, "answer_value") and resp.answer_value is not None:
                val = resp.answer_value
            elif hasattr(resp, "response_value_json") and resp.response_value_json is not None:
                val = resp.response_value_json
            elif hasattr(resp, "value_bool") and resp.value_bool is not None:
                val = resp.value_bool
            elif hasattr(resp, "value_numeric") and resp.value_numeric is not None:
                val = resp.value_numeric
            elif hasattr(resp, "value_text") and resp.value_text is not None:
                val = resp.value_text

        return val, is_unsure, is_prefer_not_to_say, is_active

    @classmethod
    def evaluate_atomic_condition(
        cls,
        condition: Dict[str, Any],
        responses_by_key: Dict[str, Any]
    ) -> Tuple[PredicateEvaluationState, str]:
        """
        Evaluates a single leaf condition against response data.
        Returns (PredicateEvaluationState, reason_string).
        """
        question_key = condition.get("question_key")
        operator = condition.get("operator", "equals").lower()
        expected_value = condition.get("expected_value")
        expected_values = condition.get("expected_values", [])

        if not question_key or question_key not in responses_by_key:
            return PredicateEvaluationState.INDETERMINATE, f"{question_key}: Response missing / unanswered"

        resp = responses_by_key[question_key]
        val, is_unsure, is_prefer_not_to_say, is_active = cls.extract_response_attributes(resp)

        # Inactive question due to conditional DAG branching
        if not is_active:
            return PredicateEvaluationState.FALSE, f"{question_key}: Inactive conditional pathway"

        # Safe Answer Principle: Unsure or Prefer Not to Say are INDETERMINATE
        if is_unsure:
            return PredicateEvaluationState.INDETERMINATE, "User selected Unsure"
        if is_prefer_not_to_say:
            return PredicateEvaluationState.INDETERMINATE, "User selected Prefer not to say"

        if val is None:
            return PredicateEvaluationState.INDETERMINATE, f"{question_key}: Null concrete value"

        # Normalization for string comparisons
        str_val = str(val).lower() if isinstance(val, (str, bool)) else val

        if operator == "equals":
            exp_str = str(expected_value).lower() if isinstance(expected_value, (str, bool)) else expected_value
            if str_val == exp_str:
                return PredicateEvaluationState.TRUE, f"{question_key} equals {expected_value}"
            return PredicateEvaluationState.FALSE, f"{question_key} ({str_val}) != {exp_str}"

        elif operator == "in":
            exp_list = [str(x).lower() if isinstance(x, (str, bool)) else x for x in expected_values]
            if str_val in exp_list:
                return PredicateEvaluationState.TRUE, f"{question_key} in {expected_values}"
            return PredicateEvaluationState.FALSE, f"{question_key} ({str_val}) not in {exp_list}"

        elif operator == "contains":
            if isinstance(val, list):
                val_list = [str(x).lower() if isinstance(x, (str, bool)) else x for x in val]
                for exp in expected_values:
                    exp_s = str(exp).lower() if isinstance(exp, (str, bool)) else exp
                    if exp_s in val_list:
                        return PredicateEvaluationState.TRUE, f"{question_key} contains {exp}"
                return PredicateEvaluationState.FALSE, f"{question_key} ({val_list}) does not contain target items"
            elif isinstance(expected_value, str) and expected_value.lower() in str_val:
                return PredicateEvaluationState.TRUE, f"{question_key} contains {expected_value}"
            return PredicateEvaluationState.FALSE, f"{question_key} does not contain {expected_value}"

        elif operator == "greater_than":
            try:
                if float(val) > float(expected_value):
                    return PredicateEvaluationState.TRUE, f"{question_key} ({val}) > {expected_value}"
                return PredicateEvaluationState.FALSE, f"{question_key} ({val}) <= {expected_value}"
            except (ValueError, TypeError):
                return PredicateEvaluationState.FALSE, f"{question_key}: Numeric conversion error on {val}"

        elif operator == "less_than":
            try:
                if float(val) < float(expected_value):
                    return PredicateEvaluationState.TRUE, f"{question_key} ({val}) < {expected_value}"
                return PredicateEvaluationState.FALSE, f"{question_key} ({val}) >= {expected_value}"
            except (ValueError, TypeError):
                return PredicateEvaluationState.FALSE, f"{question_key}: Numeric conversion error on {val}"

        return PredicateEvaluationState.FALSE, f"Unsupported operator {operator}"

    @classmethod
    def evaluate_predicate_tree(
        cls,
        trigger: Dict[str, Any],
        responses_by_key: Dict[str, Any],
        depth: int = 1
    ) -> Tuple[PredicateEvaluationState, str]:
        """
        Recursively evaluates a predicate tree (up to 3 levels) using three-valued logic:
        - all_of: TRUE if all TRUE; FALSE if any FALSE; INDETERMINATE if no FALSE and at least one INDETERMINATE.
        - any_of: TRUE if any TRUE; FALSE if all FALSE; INDETERMINATE if no TRUE and at least one INDETERMINATE.
        - none_of: TRUE only if all FALSE with concrete evidence; FALSE if any TRUE;
                   INDETERMINATE if any condition is INDETERMINATE (Safe Answer Guard).
        """
        if depth > MAX_PREDICATE_DEPTH:
            raise ValueError(
                f"Predicate nesting depth exceeds maximum allowed limit of {MAX_PREDICATE_DEPTH} levels."
            )

        if not isinstance(trigger, dict):
            return PredicateEvaluationState.FALSE, "Invalid predicate object"

        combinator = trigger.get("combinator")
        if not combinator:
            return cls.evaluate_atomic_condition(trigger, responses_by_key)

        comb_lower = combinator.lower()
        conditions = trigger.get("conditions", [])
        if not isinstance(conditions, list) or len(conditions) == 0:
            raise ValueError(f"Compound predicate '{combinator}' must contain a non-empty conditions list.")

        child_evaluations: List[Tuple[PredicateEvaluationState, str]] = []
        for child in conditions:
            child_res, child_reason = cls.evaluate_predicate_tree(child, responses_by_key, depth=depth + 1)
            child_evaluations.append((child_res, child_reason))

        states = [e[0] for e in child_evaluations]

        if comb_lower == "all_of":
            # If ANY child is FALSE, all_of evaluates to FALSE
            if PredicateEvaluationState.FALSE in states:
                first_false = next(e[1] for e in child_evaluations if e[0] == PredicateEvaluationState.FALSE)
                return PredicateEvaluationState.FALSE, f"all_of failed: {first_false}"
            # If all are TRUE, all_of evaluates to TRUE
            if all(s == PredicateEvaluationState.TRUE for s in states):
                return PredicateEvaluationState.TRUE, "all_of satisfied: all conditions met"
            # Otherwise (no FALSE, but at least one INDETERMINATE), all_of is INDETERMINATE
            first_indet = next(e[1] for e in child_evaluations if e[0] == PredicateEvaluationState.INDETERMINATE)
            return PredicateEvaluationState.INDETERMINATE, f"all_of indeterminate: {first_indet}"

        elif comb_lower == "any_of":
            # If ANY child is TRUE, any_of evaluates to TRUE
            if PredicateEvaluationState.TRUE in states:
                first_true = next(e[1] for e in child_evaluations if e[0] == PredicateEvaluationState.TRUE)
                return PredicateEvaluationState.TRUE, f"any_of satisfied: {first_true}"
            # If ALL children are FALSE, any_of evaluates to FALSE
            if all(s == PredicateEvaluationState.FALSE for s in states):
                return PredicateEvaluationState.FALSE, "any_of failed: no conditions met"
            # If no TRUE and at least one INDETERMINATE, any_of is INDETERMINATE
            first_indet = next(e[1] for e in child_evaluations if e[0] == PredicateEvaluationState.INDETERMINATE)
            return PredicateEvaluationState.INDETERMINATE, f"any_of indeterminate: {first_indet}"

        elif comb_lower == "none_of":
            # If ANY child is TRUE, none_of evaluates to FALSE
            if PredicateEvaluationState.TRUE in states:
                first_true = next(e[1] for e in child_evaluations if e[0] == PredicateEvaluationState.TRUE)
                return PredicateEvaluationState.FALSE, f"none_of failed: condition triggered ({first_true})"
            # SAFE ANSWER GUARD: If ANY child is INDETERMINATE, none_of MUST evaluate to INDETERMINATE
            if PredicateEvaluationState.INDETERMINATE in states:
                first_indet = next(e[1] for e in child_evaluations if e[0] == PredicateEvaluationState.INDETERMINATE)
                return PredicateEvaluationState.INDETERMINATE, f"none_of indeterminate: {first_indet}"
            # If ALL children are FALSE with concrete evidence, none_of evaluates to TRUE
            return PredicateEvaluationState.TRUE, "none_of satisfied: all conditions excluded with concrete evidence"

        raise ValueError(f"Unknown combinator: {combinator}")

    @classmethod
    def evaluate_rule_to_state(
        cls,
        rule_trigger_criteria: Dict[str, Any],
        relevant_question_keys: List[str],
        responses_by_key: Dict[str, Any]
    ) -> Tuple[RuleEvaluationState, str]:
        """
        Maps a clinical rule's evaluation to one of the canonical four states:
        - NOT_APPLICABLE: If all relevant questions are inactive in the DAG.
        - TRIGGERED: If the predicate evaluates to TRUE.
        - INDETERMINATE: If the predicate evaluates to INDETERMINATE.
        - EXPLICIT_NON_TRIGGER: If the predicate evaluates to FALSE with concrete active responses.
        """
        # Check if all relevant questions are conditionally inactive
        all_inactive = True
        has_any_response = False
        for qk in relevant_question_keys:
            if qk in responses_by_key:
                has_any_response = True
                resp = responses_by_key[qk]
                _, _, _, is_active = cls.extract_response_attributes(resp)
                if is_active:
                    all_inactive = False
                    break

        if has_any_response and all_inactive:
            return RuleEvaluationState.NOT_APPLICABLE, "Relevant questions deactivated by conditional DAG"

        # Evaluate predicate tree
        try:
            pred_state, reason = cls.evaluate_predicate_tree(rule_trigger_criteria, responses_by_key)
        except Exception as e:
            return RuleEvaluationState.INDETERMINATE, f"Predicate evaluation error: {str(e)}"

        if pred_state == PredicateEvaluationState.TRUE:
            return RuleEvaluationState.TRIGGERED, reason
        elif pred_state == PredicateEvaluationState.INDETERMINATE:
            return RuleEvaluationState.INDETERMINATE, reason
        else:
            return RuleEvaluationState.EXPLICIT_NON_TRIGGER, reason
