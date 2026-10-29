import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/90",
        outline: "border border-input bg-card hover:bg-muted",
        ghost: "hover:bg-muted",
        soft: "bg-accent text-accent-foreground hover:bg-accent/80",
        destructive: "bg-critical text-white shadow-sm hover:bg-critical/90",
        link: "text-primary underline-offset-4 hover:underline px-0 h-auto",
      },
      size: { default: "h-10 px-4", sm: "h-8 rounded-md px-3 text-xs", lg: "h-11 px-6 text-[15px]", icon: "h-9 w-9" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading, disabled, children, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} disabled={disabled || loading}
            aria-busy={loading || undefined} {...props}>
        {asChild ? children : <>{loading && <Loader2 className="animate-spin" aria-hidden />}{children}</>}
      </Comp>
    );
  },
);
Button.displayName = "Button";
