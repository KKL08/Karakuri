export type UnifiedDiffInput = {
  fromFile: string;
  toFile: string;
  before: string;
  after: string;
};

type DiffLine = {
  prefix: " " | "-" | "+";
  value: string;
};

export function createUnifiedDiff(input: UnifiedDiffInput): string {
  const beforeLines = splitContent(input.before);
  const afterLines = splitContent(input.after);
  const hunkLines = createHunkLines(beforeLines, afterLines);

  return [
    `--- ${input.fromFile}`,
    `+++ ${input.toFile}`,
    `@@ -${rangeStart(beforeLines)},${beforeLines.length} +${rangeStart(afterLines)},${afterLines.length} @@`,
    ...hunkLines.map((line) => `${line.prefix}${line.value}`),
    "",
  ].join("\n");
}

function splitContent(content: string): string[] {
  if (content.length === 0) return [];

  const lines = content.replace(/\r\n/g, "\n").split("\n");
  if (lines.at(-1) === "") {
    lines.pop();
  }
  return lines;
}

function createHunkLines(beforeLines: string[], afterLines: string[]): DiffLine[] {
  const table = createLcsTable(beforeLines, afterLines);
  const lines: DiffLine[] = [];
  let beforeIndex = 0;
  let afterIndex = 0;

  while (beforeIndex < beforeLines.length && afterIndex < afterLines.length) {
    if (beforeLines[beforeIndex] === afterLines[afterIndex]) {
      lines.push({ prefix: " ", value: beforeLines[beforeIndex] });
      beforeIndex += 1;
      afterIndex += 1;
    } else if (table[beforeIndex + 1][afterIndex] >= table[beforeIndex][afterIndex + 1]) {
      lines.push({ prefix: "-", value: beforeLines[beforeIndex] });
      beforeIndex += 1;
    } else {
      lines.push({ prefix: "+", value: afterLines[afterIndex] });
      afterIndex += 1;
    }
  }

  while (beforeIndex < beforeLines.length) {
    lines.push({ prefix: "-", value: beforeLines[beforeIndex] });
    beforeIndex += 1;
  }

  while (afterIndex < afterLines.length) {
    lines.push({ prefix: "+", value: afterLines[afterIndex] });
    afterIndex += 1;
  }

  return lines;
}

function createLcsTable(beforeLines: string[], afterLines: string[]): number[][] {
  const table = Array.from({ length: beforeLines.length + 1 }, () => Array(afterLines.length + 1).fill(0));

  for (let beforeIndex = beforeLines.length - 1; beforeIndex >= 0; beforeIndex -= 1) {
    for (let afterIndex = afterLines.length - 1; afterIndex >= 0; afterIndex -= 1) {
      table[beforeIndex][afterIndex] =
        beforeLines[beforeIndex] === afterLines[afterIndex]
          ? table[beforeIndex + 1][afterIndex + 1] + 1
          : Math.max(table[beforeIndex + 1][afterIndex], table[beforeIndex][afterIndex + 1]);
    }
  }

  return table;
}

function rangeStart(lines: string[]): number {
  return lines.length === 0 ? 0 : 1;
}
