/** Convert markdown-like AI output into clean plain text for UI display. */
export function formatHumanText(input: string | null | undefined): string {
  if (!input) {
    return "";
  }

  let text = input.replace(/\r\n/g, "\n").trim();

  // Remove markdown emphasis markers.
  text = text.replace(/\*\*(.*?)\*\*/g, "$1");
  text = text.replace(/__(.*?)__/g, "$1");
  text = text.replace(/\*([^*\n]+)\*/g, "$1");
  text = text.replace(/_([^_\n]+)_/g, "$1");

  // Normalize list markers.
  text = text
    .split("\n")
    .map((line) => line
      .replace(/^\s*[*-]\s+/, "• ")
      .replace(/^\s*(\d+)\.\s+/, "$1. ")
      .trimEnd()
    )
    .join("\n");

  // Normalize whitespace while preserving paragraph breaks.
  text = text
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return text;
}
