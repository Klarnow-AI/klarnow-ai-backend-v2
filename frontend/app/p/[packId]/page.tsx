import { publicApi } from "@/api_requests/public";
import { ConversionPageRenderer } from "@/components/conversion-page/ConversionPageRenderer";

export const dynamic = "force-dynamic";

export default async function PublicConversionPage({
  params,
}: {
  params: Promise<{ packId: string }>;
}) {
  const { packId } = await params;

  const preview = await publicApi.getPublishedConversionPage(packId);

  return (
    <ConversionPageRenderer packId={packId} structure={preview.structure} mode="public" />
  );
}

