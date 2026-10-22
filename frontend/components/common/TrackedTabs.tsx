"use client";

import { Tabs } from "@/components/ui/tabs";
import { track } from "@/lib/analytics/client";

export default function TrackedTabs(props: React.ComponentProps<typeof Tabs>) {
  return (
    <Tabs
      {...props}
      onValueChange={(value, eventDetails) => {
        track("project_tab_viewed", { tab: String(value) });
        props.onValueChange?.(value, eventDetails);
      }}
    />
  );
}
