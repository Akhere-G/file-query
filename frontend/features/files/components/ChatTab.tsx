"use client";

import { Input } from "@/components/ui/input";

const ChatTab = () => {
  return (
    <div className="p-4 h-full relative flex justify-end flex-col">
      <div className=""></div>
      <Input className="bg-secondary rounded-md border-0 sticky bottom-0 pl-4" />
    </div>
  );
};

export default ChatTab;
