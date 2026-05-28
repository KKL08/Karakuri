export type BlindComparisonWinner = "output_a" | "output_b" | "tie";

export type BlindComparison = {
  winner: BlindComparisonWinner;
  reason: string;
};

type OutputScore = {
  score: number;
  hasExpectedSignal: boolean;
};

export function compareBlind(input: { outputA: string; outputB: string; expected: string }): BlindComparison {
  const outputA = input.outputA.trim();
  const outputB = input.outputB.trim();
  const expected = input.expected.trim();

  if (!outputA && !outputB) {
    return { winner: "tie", reason: "两份输出都为空，无法做有效比较。" };
  }

  if (!expected) {
    return { winner: "tie", reason: "expected 为空，这个轻量启发式无法判断哪份输出更贴近目标。" };
  }

  const a = scoreOutput(outputA, expected);
  const b = scoreOutput(outputB, expected);
  const delta = Math.abs(a.score - b.score);

  if (!a.hasExpectedSignal && !b.hasExpectedSignal) {
    return { winner: "tie", reason: "两份输出都没有明显命中 expected，这个轻量启发式不判胜负。" };
  }

  if (delta <= 0.25) {
    return { winner: "tie", reason: "两份输出与 expected 的轻量启发式匹配度接近。" };
  }

  return a.score > b.score
    ? {
        winner: "output_a",
        reason: "output_a 对 normalized expected 的命中更充分；长度只作为很弱的辅助因素。这是轻量启发式，不是模型评审结论。",
      }
    : {
        winner: "output_b",
        reason: "output_b 对 normalized expected 的命中更充分；长度只作为很弱的辅助因素。这是轻量启发式，不是模型评审结论。",
      };
}

function scoreOutput(output: string, expected: string): OutputScore {
  const normalizedOutput = normalizeText(output);
  const normalizedExpected = normalizeText(expected);

  if (!normalizedOutput || !normalizedExpected) {
    return { score: 0, hasExpectedSignal: false };
  }

  if (normalizedOutput === normalizedExpected) {
    return { score: 100, hasExpectedSignal: true };
  }

  if (normalizedOutput.includes(normalizedExpected)) {
    return { score: 90 + weakLengthBonus(normalizedOutput), hasExpectedSignal: true };
  }

  const expectedTerms = extractTerms(normalizedExpected);
  const matchedTerms = expectedTerms.filter((term) => normalizedOutput.includes(term));

  if (matchedTerms.length === 0) {
    return { score: 0, hasExpectedSignal: false };
  }

  const termCoverage = matchedTerms.length / expectedTerms.length;
  const characterCoverage = charCoverage(normalizedOutput, normalizedExpected);

  return {
    score: termCoverage * 50 + characterCoverage * 10 + weakLengthBonus(normalizedOutput),
    hasExpectedSignal: true,
  };
}

function normalizeText(text: string): string {
  return text
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[\p{P}\p{S}]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractTerms(text: string): string[] {
  const asciiTerms = text.match(/[a-z0-9_]+/g)?.filter((term) => term.length >= 2) ?? [];
  const cjkTerms = text.match(/[\u4e00-\u9fff]{2,}/g) ?? [];
  const cjkBigrams = cjkTerms.flatMap((term) => {
    const terms: string[] = [];
    for (let index = 0; index <= term.length - 2; index += 1) {
      terms.push(term.slice(index, index + 2));
    }
    return terms;
  });

  return [...new Set([...asciiTerms, ...cjkBigrams])];
}

function charCoverage(output: string, expected: string): number {
  const expectedChars = [...new Set([...expected].filter((char) => /\S/u.test(char)))];
  if (expectedChars.length === 0) return 0;

  const matched = expectedChars.filter((char) => output.includes(char)).length;
  return matched / expectedChars.length;
}

function weakLengthBonus(output: string): number {
  return Math.min(output.length / 200, 0.2);
}
