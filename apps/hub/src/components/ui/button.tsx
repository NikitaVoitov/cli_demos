import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Slot } from "radix-ui"

// Variants follow SDS-Web Button: pill shape, primary/secondary actions, token-driven focus ring.
const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 border border-transparent whitespace-nowrap text-button transition-colors outline-none select-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus-ring disabled:pointer-events-none disabled:bg-disabled disabled:text-muted-foreground [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary-hover",
        outline: "border-secondary-border bg-transparent text-foreground hover:bg-secondary-hover",
        ghost: "text-muted-foreground hover:bg-secondary-hover hover:text-foreground",
        link: "text-foreground underline underline-offset-4 hover:text-accent-pink",
      },
      size: {
        default: "h-9 rounded-full px-4",
        pill: "h-9 rounded-full px-5",
        sm: "h-8 rounded-full px-3 text-[13px]",
        icon: "size-9 rounded-md",
        "icon-sm": "size-8 rounded-md",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
