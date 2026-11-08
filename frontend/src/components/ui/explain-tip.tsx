import { useMediaQuery } from "@/hooks/useMediaQuery";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

/**
 * A short explanation of a term or figure: a tooltip with a mouse (hover and
 * keyboard focus). A tap never opens a tooltip, so on touch screens it is a
 * popover that a tap opens and a tap elsewhere closes.
 */
export function ExplainTip({ explanation, children }: { explanation: string; children: React.ReactElement }) {
  const touch = useMediaQuery("(hover: none)");
  if (touch) {
    return (
      <Popover>
        <PopoverTrigger asChild>{children}</PopoverTrigger>
        <PopoverContent className="z-[3000] w-64 px-3 py-2 text-[14px] leading-snug">{explanation}</PopoverContent>
      </Popover>
    );
  }
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent>{explanation}</TooltipContent>
    </Tooltip>
  );
}
