import { redirect } from "next/navigation";

export default function ReportVerifyRedirect({ params }: { params: { reference: string } }) {
  redirect(`/verify?ref=${encodeURIComponent(params.reference)}`);
}
