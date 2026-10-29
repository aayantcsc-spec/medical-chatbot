/* Radix-based Dialog, Sheet (mobile drawer), DropdownMenu, Tabs, Checkbox, Tooltip. */
import type { ComponentPropsWithoutRef, ReactNode } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as Dropdown from "@radix-ui/react-dropdown-menu";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------- Dialog
export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;
export function DialogContent({ title, description, children, className }: {
  title: string; description?: ReactNode; children?: ReactNode; className?: string;
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-slate-950/40 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=open]:fade-in-0" />
      <DialogPrimitive.Content className={cn("fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-xl border bg-card p-6 shadow-lift data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95", className)}>
        <DialogPrimitive.Title className="text-lg font-semibold">{title}</DialogPrimitive.Title>
        {description ? <DialogPrimitive.Description className="mt-1.5 text-sm text-muted-foreground">{description}</DialogPrimitive.Description>
                     : <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>}
        <div className="mt-4">{children}</div>
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm text-muted-foreground hover:text-foreground" aria-label="Close">
          <X className="size-4" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

// ---------------------------------------------------------------- Sheet (left drawer)
export function Sheet({ open, onOpenChange, title, children }: {
  open: boolean; onOpenChange: (o: boolean) => void; title: string; children: ReactNode;
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-slate-950/50 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content className="fixed inset-y-0 left-0 z-50 flex w-[min(20rem,85vw)] flex-col bg-sidebar text-sidebar-foreground shadow-lift data-[state=open]:animate-in data-[state=open]:slide-in-from-left">
          <DialogPrimitive.Title className="sr-only">{title}</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

// ---------------------------------------------------------------- Dropdown
export const DropdownMenu = Dropdown.Root;
export const DropdownMenuTrigger = Dropdown.Trigger;
export function DropdownMenuContent({ children, align = "end", className }: { children: ReactNode; align?: "start" | "end"; className?: string }) {
  return (
    <Dropdown.Portal>
      <Dropdown.Content align={align} sideOffset={6}
        className={cn("z-50 min-w-[12rem] rounded-lg border bg-card p-1 text-card-foreground shadow-lift data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95", className)}>
        {children}
      </Dropdown.Content>
    </Dropdown.Portal>
  );
}
export function DropdownMenuItem({ className, ...p }: ComponentPropsWithoutRef<typeof Dropdown.Item>) {
  return <Dropdown.Item className={cn("flex cursor-pointer select-none items-center gap-2 rounded-md px-2.5 py-2 text-sm outline-none data-[highlighted]:bg-muted data-[disabled]:opacity-50 [&_svg]:size-4", className)} {...p} />;
}
export const DropdownMenuLabel = ({ children }: { children: ReactNode }) => (
  <Dropdown.Label className="px-2.5 py-1.5 text-xs font-medium text-muted-foreground">{children}</Dropdown.Label>
);
export const DropdownMenuSeparator = () => <Dropdown.Separator className="my-1 h-px bg-border" />;

// ---------------------------------------------------------------- Tabs
export const Tabs = TabsPrimitive.Root;
export function TabsList({ className, ...p }: ComponentPropsWithoutRef<typeof TabsPrimitive.List>) {
  return <TabsPrimitive.List className={cn("inline-flex h-auto flex-wrap items-center gap-1 rounded-lg bg-muted p-1", className)} {...p} />;
}
export function TabsTrigger({ className, ...p }: ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>) {
  return <TabsPrimitive.Trigger className={cn("inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm [&_svg]:size-4", className)} {...p} />;
}
export const TabsContent = ({ className, ...p }: ComponentPropsWithoutRef<typeof TabsPrimitive.Content>) => (
  <TabsPrimitive.Content className={cn("mt-5 focus-visible:outline-none", className)} {...p} />
);

// ---------------------------------------------------------------- Checkbox
export function Checkbox({ className, ...p }: ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>) {
  return (
    <CheckboxPrimitive.Root className={cn("peer size-4 shrink-0 rounded border border-input bg-card shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground", className)} {...p}>
      <CheckboxPrimitive.Indicator className="flex items-center justify-center"><Check className="size-3" strokeWidth={3} /></CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}

// ---------------------------------------------------------------- Tooltip
export const TooltipProvider = TooltipPrimitive.Provider;
export function Tooltip({ content, children, side = "top" }: { content: ReactNode; children: ReactNode; side?: "top" | "right" | "bottom" | "left" }) {
  return (
    <TooltipPrimitive.Root delayDuration={200}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content side={side} sideOffset={6}
          className="z-50 max-w-xs rounded-md bg-foreground px-2.5 py-1.5 text-xs text-background shadow-lift data-[state=delayed-open]:animate-in data-[state=delayed-open]:fade-in-0">
          {content}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
