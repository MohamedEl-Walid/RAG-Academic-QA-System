// Node 22+ ships a built-in localStorage global that throws without
// --localstorage-file. Delete it so Next.js SSR doesn't crash.
if (typeof globalThis.localStorage !== "undefined") {
  try {
    globalThis.localStorage.getItem("__test__");
  } catch {
    delete globalThis.localStorage;
  }
}
