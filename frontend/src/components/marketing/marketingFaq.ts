export const MARKETING_FAQ = [
  {
    cat: "Registration",
    items: [
      {
        q: "How do I create an account?",
        a: "Click Get started on the home page, verify your email (or use Google sign-up), then open Enrollment from the menu to capture both palms.",
      },
      {
        q: "Is palm enrollment required?",
        a: "Enrollment is optional at signup but required for palm sign-in and live recognition.",
      },
    ],
  },
  {
    cat: "Privacy",
    items: [
      {
        q: "What data is stored?",
        a: "We store mathematical vein embeddings for matching. Enrollment images are retained in your dataset folder for audit.",
      },
      {
        q: "Can I delete my account?",
        a: "Contact us via the Contact page to request account and biometric data deletion.",
      },
    ],
  },
  {
    cat: "Hardware",
    items: [
      {
        q: "What scanner is needed?",
        a: "An NIR palm vein sensor connected to the backend. The web app talks to the local API on port 8000.",
      },
    ],
  },
] as const
