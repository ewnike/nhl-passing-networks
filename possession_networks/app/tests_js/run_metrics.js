// Reads a JSON list of square matrices from argv[2], prints analyze() output as JSON.
const fs = require("fs");
const M = require("../metrics.js");
const graphs = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
console.log(JSON.stringify(graphs.map((W) => M.analyze(W))));
