import { strings, type StringKey } from "./strings";

export function useTranslation() {
  return function t(key: StringKey): string {
    return strings[key];
  };
}
