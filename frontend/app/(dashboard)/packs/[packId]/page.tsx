import { redirect } from "next/navigation";

export default async function PackPage({
  params,
}: {
  params: Promise<{ packId: string }>;
}) {
  const { packId } = await params;
  redirect(`/chat?pack=${packId}`);
}
