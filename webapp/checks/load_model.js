// Loads the browser model (everything in webapp/index.html's script before the UI code) into Node.
// Usage: const M = require("./load_model"); M.simPack(...), M.runAll(...), M.DEFAULTS, ...
const fs = require("fs"), path = require("path");
const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const start = html.indexOf('"use strict";'), end = html.indexOf("// ---------------------------------------------------------------- controls");
if (start < 0 || end < 0) throw new Error("model markers not found in index.html");
const names = ["DEFAULTS", "CAL", "YEARS", "SPY", "K", "DT", "clone", "simPack", "runAll", "econPack", "econHorizon", "pct"];
module.exports = new Function(html.slice(start, end) + `\nreturn { ${names.join(", ")} };`)();
