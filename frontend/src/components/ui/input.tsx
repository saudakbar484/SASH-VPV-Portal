import * as React from "react"

import { cn } from "@/lib/utils"

export const fieldClassName =
  "app-field disabled:cursor-not-allowed disabled:opacity-55"

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => (
  <input type={type} ref={ref} className={cn(fieldClassName, className)} {...props} />
))
Input.displayName = "Input"
