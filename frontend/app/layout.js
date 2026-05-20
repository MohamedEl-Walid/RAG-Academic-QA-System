import "./globals.css";

export const metadata = {
  title: "NeuralLearn — AI-Powered Education Platform",
  description:
    "An intelligent, context-aware learning assistant powered by RAG. Ask questions, generate quizzes, visualize concepts, and master any subject.",
  keywords: ["AI", "education", "learning", "RAG", "quiz", "diagram"],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="true" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
