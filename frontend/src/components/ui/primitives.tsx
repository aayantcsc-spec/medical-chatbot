/* Small shadcn-style primitives: Card, Badge, Input, Textarea, Label, Select, Skeleton, Alert, Progress, Separator. */
import { forwardRef, type HTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes,
         type TextareaHTMLAttributes } from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { cva, type VariantProps } from "class-variance-authority";
import { AlertTriangle, CheckCircle2, Info, OctagonAlert } from "lucide-react";
import { cn } from "@/lib/utils";

export const Card = ({ className, ...p }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("rounded-xl border bg-card text-card-foreground shadow-card", className)} {...p} />
);
export const CardHeader = ({ className, ...p }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col gap-1 p-5 pb-3", className)} {...p} />
);
export const CardTitle = ({ className, ...p }: HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={cn("text-base font-semibold leading-tight", className)} {...p} />
);
export const CardDescription = ({ className, ...p }: HTMLAttributes<HTMLParagraphElement>) => (
  <p className={cn("text-sm text-muted-foreground", className)} {...p} />
);
export const CardContent = ({ className, ...p }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("p-5 pt-0", className)} {...p} />
);

const badgeVariants = cva("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap", {
  variants: {
    variant: {
      default: "border-transparent bg-accent text-accent-foreground",
      outline: "text-muted-foreground",
      success: "border-transparent bg-success-soft text-success",
      warning: "border-transparent bg-warning-soft text-warning",
      critical: "border-transparent bg-critical-soft text-critical",
      secondary: "border-transparent bg-secondary/10 text-secondary",
      muted: "border-transparent bg-muted text-muted-foreground",
    },
  },
  defaultVariants: { variant: "default" },
});
export const Badge = ({ className, variant, ...p }: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) => (
  <span className={cn(badgeVariants({ variant }), className)} {...p} />
);

const field = "flex w-full rounded-md border border-input bg-card px-3 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-critical";
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(({ className, ...p }, ref) => (
  <input ref={ref} className={cn(field, "h-10 py-2", className)} {...p} />
));
Input.displayName = "Input";
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...p }, ref) => (
  <textarea ref={ref} className={cn(field, "min-h-[80px] py-2 leading-relaxed", className)} {...p} />
));
Textarea.displayName = "Textarea";
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(({ className, ...p }, ref) => (
  <select ref={ref} className={cn(field, "h-10 py-2 pr-8", className)} {...p} />
));
Select.displayName = "Select";
export const Label = forwardRef<HTMLLabelElement, LabelPrimitive.LabelProps>(({ className, ...p }, ref) => (
  <LabelPrimitive.Root ref={ref} className={cn("text-sm font-medium leading-none", className)} {...p} />
));
Label.displayName = "Label";

export const FieldError = ({ children, id }: { children?: ReactNode; id?: string }) =>
  children ? <p id={id} role="alert" className="text-xs font-medium text-critical">{children}</p> : null;

export const Skeleton = ({ className, ...p }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("animate-pulse rounded-md bg-muted", className)} aria-hidden {...p} />
);

export const Separator = ({ className }: { className?: string }) => <div role="separator" className={cn("h-px w-full bg-border", className)} />;

const alertStyles = {
  info: { box: "border-primary/20 bg-accent text-accent-foreground", Icon: Info },
  success: { box: "border-success/20 bg-success-soft text-success", Icon: CheckCircle2 },
  warning: { box: "border-warning/30 bg-warning-soft text-warning", Icon: AlertTriangle },
  critical: { box: "border-critical/30 bg-critical-soft text-critical", Icon: OctagonAlert },
};
export function Alert({ variant = "info", title, children, className, action }: {
  variant?: keyof typeof alertStyles; title?: ReactNode; children?: ReactNode; className?: string; action?: ReactNode;
}) {
  const { box, Icon } = alertStyles[variant];
  return (
    <div role={variant === "critical" ? "alert" : "status"} className={cn("flex gap-3 rounded-lg border p-3.5 text-sm", box, className)}>
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1 space-y-1">
        {title && <p className="font-semibold leading-tight">{title}</p>}
        {children && <div className="text-foreground/80 [&_a]:underline">{children}</div>}
      </div>
      {action}
    </div>
  );
}

export function Progress({ value, label, className }: { value: number; label?: string; className?: string }) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(v)} aria-label={label}
         className={cn("h-2 w-full overflow-hidden rounded-full bg-muted", className)}>
      <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${v}%` }} />
    </div>
  );
}
