import { useEffect } from "react"
import { useNavigate } from "react-router-dom"

/** Redirect legacy /faq to the FAQ section on the home page. */
export function FaqRedirect() {
  const navigate = useNavigate()

  useEffect(() => {
    navigate("/", { replace: true })
    const scroll = () => document.getElementById("faq")?.scrollIntoView({ behavior: "smooth" })
    requestAnimationFrame(() => requestAnimationFrame(scroll))
  }, [navigate])

  return null
}
