"use client";

import { useParams } from "next/navigation";
import {
  Panel,
  Group,
  Separator,
  useDefaultLayout,
} from "react-resizable-panels";
import { BuilderChatPanel } from "../_components/builder-chat-panel";
import { AdPreviewPanel } from "./_components/ad-preview-panel";

function ResizableLayout({ packId }: { packId: string }) {
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({
    id: "ad-factory-panel-layout",
    storage: typeof window !== "undefined" ? localStorage : undefined,
  });

  return (
    <Group
      orientation="horizontal"
      defaultLayout={defaultLayout}
      onLayoutChanged={onLayoutChanged}
      className="flex-1 min-h-0"
    >
      <Panel id="chat" defaultSize="30%" minSize="20%" maxSize="50%">
        <div className="flex flex-col h-full overflow-hidden">
          <BuilderChatPanel
            title="Ad Factory"
            apiRoute="/api/generate-poster"
            emptyStateTitle="Create a video ad"
            emptyStateDescription="Describe the ad you'd like to create and Klaro will generate it for you."
          />
        </div>
      </Panel>

      <Separator className="w-1.5 bg-transparent hover:bg-primary/50 transition-colors duration-150 cursor-col-resize" />

      <Panel id="preview" defaultSize="70%" minSize="50%">
        <div className="h-full overflow-hidden">
          <AdPreviewPanel />
        </div>
      </Panel>
    </Group>
  );
}

export default function AdFactoryPage() {
  const params = useParams();
  const packId = params.packId as string | undefined;

  if (!packId) return null;

  return (
    <div className="flex flex-1 min-h-0 overflow-hidden p-4">
      <ResizableLayout packId={packId} />
    </div>
  );
}
