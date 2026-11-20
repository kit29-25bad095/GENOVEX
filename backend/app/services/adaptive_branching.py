"""
Adaptive Questionnaire Branching Engine (Phase 6)
=================================================
Provides deterministic DAG graph resolution, Kahn's algorithm cycle detection,
parent reference validation, visibility evaluation, and transitive descendant tracking
for adaptive questionnaire pathways.
"""

from typing import List, Dict, Any, Optional, Set, Union
from fastapi import HTTPException, status
from collections import deque, defaultdict


class AdaptiveBranchingService:
    """
    Core service for topological DAG validation, conditional visibility evaluation,
    and downstream descendant resolution in adaptive questionnaires.
    """

    @classmethod
    def _extract_question_attr(cls, question: Union[Any, Dict[str, Any]], attr: str, default: Any = None) -> Any:
        if isinstance(question, dict):
            return question.get(attr, default)
        return getattr(question, attr, default)

    @classmethod
    def validate_questionnaire_dag(cls, questions: List[Union[Any, Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Validates the dependency graph of a questionnaire version:
        1. Detects direct and indirect cycles using Kahn's algorithm (topological sort).
        2. Detects dangling parent references (referencing keys not present in the version).
        3. Detects unreachable trigger values (trigger values not in parent options).
        
        Raises HTTPException(status_code=400) if validation fails.
        Returns validation summary dictionary if successful.
        """
        if not questions:
            return {"valid": True, "total_questions": 0, "conditional_count": 0}

        questions_by_key: Dict[str, Any] = {}
        in_degree: Dict[str, int] = defaultdict(int)
        adjacency_list: Dict[str, List[str]] = defaultdict(list)
        all_keys: Set[str] = set()

        # Step 1: Index questions and check duplicates
        for q in questions:
            key = cls._extract_question_attr(q, "question_key")
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid question: question_key is required for all questions"
                )
            if key in all_keys:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate question_key detected in questionnaire: '{key}'"
                )
            all_keys.add(key)
            questions_by_key[key] = q
            in_degree[key] = 0

        conditional_count = 0

        # Step 2: Build directed edges (Parent -> Child)
        for key, q in questions_by_key.items():
            parent_key = cls._extract_question_attr(q, "conditional_parent_key")
            if parent_key:
                conditional_count += 1
                # Dangling reference check
                if parent_key not in all_keys:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid conditional branching: question '{key}' references non-existent parent key '{parent_key}'"
                    )
                # Self-loop check
                if parent_key == key:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Circular dependency detected: question '{key}' cannot depend on itself"
                    )

                # Check trigger values validity against parent options if options exist
                parent_q = questions_by_key[parent_key]
                parent_opts = cls._extract_question_attr(parent_q, "options_json") or []
                trigger_values = cls._extract_question_attr(q, "conditional_trigger_values") or []

                if parent_opts and trigger_values and isinstance(parent_opts, list):
                    opt_keys = {
                        str(opt.get("key") if isinstance(opt, dict) else opt).strip().lower()
                        for opt in parent_opts
                    }
                    if opt_keys:
                        # Check that at least one trigger value matches an option key
                        has_valid_match = False
                        for tv in trigger_values:
                            if str(tv).strip().lower() in opt_keys:
                                has_valid_match = True
                                break
                        if not has_valid_match:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=(
                                    f"Unreachable trigger value in question '{key}': trigger values {trigger_values} "
                                    f"do not match any option in parent '{parent_key}' ({list(opt_keys)})"
                                )
                            )

                # Directed edge: parent -> child
                adjacency_list[parent_key].append(key)
                in_degree[key] += 1

        # Step 3: Kahn's Algorithm for Topological Sort & Cycle Detection
        queue = deque([k for k in all_keys if in_degree[k] == 0])
        visited_count = 0
        topological_order: List[str] = []

        while queue:
            current = queue.popleft()
            topological_order.append(current)
            visited_count += 1

            for neighbor in adjacency_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(all_keys):
            # A cycle exists! Identify the cyclic nodes
            cycle_nodes = [k for k in all_keys if in_degree[k] > 0]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Circular dependency detected in questionnaire DAG involving questions: {cycle_nodes}"
            )

        return {
            "valid": True,
            "total_questions": len(all_keys),
            "conditional_count": conditional_count,
            "topological_order": topological_order
        }

    @classmethod
    def evaluate_question_visibility(
        cls,
        question: Union[Any, Dict[str, Any]],
        saved_answers: Dict[str, Any]
    ) -> bool:
        """
        Evaluates whether a question is currently visible based on saved answers:
        - If root question (no conditional_parent_key): always True.
        - If conditional: parent must be present in saved_answers, not unsure, not prefer-not-to-say,
          and parent answer_value must match at least one trigger value.
        """
        parent_key = cls._extract_question_attr(question, "conditional_parent_key")
        if not parent_key:
            return True

        if parent_key not in saved_answers:
            return False

        parent_resp = saved_answers[parent_key]
        
        # Extract flags and value
        is_unsure = False
        is_prefer_not_to_say = False
        parent_val = None

        if isinstance(parent_resp, dict):
            is_unsure = parent_resp.get("is_unsure", False)
            is_prefer_not_to_say = parent_resp.get("is_prefer_not_to_say", False)
            parent_val = parent_resp.get("answer_value")
            # If parent pathway was deactivated, it cannot trigger child
            if parent_resp.get("conditional_pathway_active") is False:
                return False
        else:
            is_unsure = getattr(parent_resp, "is_unsure", False)
            is_prefer_not_to_say = getattr(parent_resp, "is_prefer_not_to_say", False)
            parent_val = getattr(parent_resp, "answer_value", None)
            if getattr(parent_resp, "conditional_pathway_active", True) is False:
                return False

        # Safe Answer: Unsure or declined never triggers follow-up pathways
        if is_unsure or is_prefer_not_to_say or parent_val is None:
            return False

        # Evaluate against trigger values
        trigger_values = cls._extract_question_attr(question, "conditional_trigger_values") or []
        if not trigger_values:
            # If conditional_parent_key is set but trigger_values empty, fallback to non-empty
            return True

        # Normalized string comparison
        if isinstance(parent_val, list):
            parent_str_set = {str(x).strip().lower() for x in parent_val}
            for tv in trigger_values:
                if str(tv).strip().lower() in parent_str_set:
                    return True
        else:
            parent_str = str(parent_val).strip().lower()
            for tv in trigger_values:
                if str(tv).strip().lower() == parent_str:
                    return True

        return False

    @classmethod
    def get_descendant_tree(
        cls,
        parent_key: str,
        questions: List[Union[Any, Dict[str, Any]]]
    ) -> List[str]:
        """
        Returns all transitive descendant question keys that directly or indirectly
        depend on parent_key, in topological order.
        """
        adjacency: Dict[str, List[str]] = defaultdict(list)
        for q in questions:
            pkey = cls._extract_question_attr(q, "conditional_parent_key")
            qkey = cls._extract_question_attr(q, "question_key")
            if pkey and qkey:
                adjacency[pkey].append(qkey)

        descendants: List[str] = []
        visited: Set[str] = set()
        queue = deque([parent_key])

        while queue:
            curr = queue.popleft()
            for child in adjacency.get(curr, []):
                if child not in visited:
                    visited.add(child)
                    descendants.append(child)
                    queue.append(child)

        return descendants

    @classmethod
    def calculate_active_pathway(
        cls,
        questions: List[Union[Any, Dict[str, Any]]],
        saved_answers: Dict[str, Any]
    ) -> Set[str]:
        """
        Computes the complete set of question keys that are currently active
        based on sequential evaluation of dependencies.
        """
        active_keys: Set[str] = set()
        # Sort questions by display order
        sorted_questions = sorted(
            questions,
            key=lambda x: (
                cls._extract_question_attr(x, "display_order", 0)
            )
        )

        for q in sorted_questions:
            q_key = cls._extract_question_attr(q, "question_key")
            if cls.evaluate_question_visibility(q, saved_answers):
                active_keys.add(q_key)

        return active_keys
