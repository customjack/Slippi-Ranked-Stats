/**
 * Browser-compatible stub for iconv-lite.
 * slippi-js uses it to decode Shift_JIS player names and UTF-8 IDs during _process().
 * The browser's native TextDecoder supports both encodings, so we don't need the real package.
 */

const LABEL_MAP: Record<string, string> = {
  "Shift_JIS": "shift-jis",
  "shift-jis": "shift-jis",
  "utf8": "utf-8",
  "utf-8": "utf-8",
};

function decode(buf: Uint8Array | number[], encoding: string): string {
  const label = LABEL_MAP[encoding] ?? encoding;
  try {
    return new TextDecoder(label).decode(
      buf instanceof Uint8Array ? buf : new Uint8Array(buf as number[])
    );
  } catch {
    return new TextDecoder("utf-8").decode(
      buf instanceof Uint8Array ? buf : new Uint8Array(buf as number[])
    );
  }
}

function encode(str: string, encoding: string): Uint8Array {
  return new TextEncoder().encode(str);
}

function encodingExists(_encoding: string): boolean {
  return true;
}

export { decode, encode, encodingExists };
export default { decode, encode, encodingExists };
