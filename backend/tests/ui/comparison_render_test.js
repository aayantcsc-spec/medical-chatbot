// Pure-render tests for static/js/comparison.js.  Run:  node tests/ui/comparison_render_test.js
const assert = require("assert");
const C = require("../../static/js/comparison.js");
const sc = (o) => ({ eligible: true, correctness: null, safety: 100, quality: 80, speed: 50, overall: 80, inference_ms: 10, unavailable: ["correctness"], ...o });
const winnerSel = { status: "winner", winner_key: "ml", winner_name: "ML - TF-IDF + SVM", winner_score: 91.2, reason: "r", scores: { rule: sc({ overall: 70 }), ml: sc({ overall: 91.2 }), dl: sc({ overall: 60 }) } };
const tieSel = { status: "tie", tied_keys: ["rule", "ml"], fastest_key: "ml", headline: "Tie - no single best response", reason: "t", scores: winnerSel.scores };
const noneSel = { status: "undetermined", headline: "Unable to determine a reliable winner", reason: "x", scores: { rule: sc({ eligible: false, overall: null, excluded_reason: "reply is in Hinglish" }) } };

// the badge appears on exactly the backend's winner
const tags = C.ARCH.filter((k) => C.cardTag(winnerSel, k).includes("Best Response"));
assert.deepStrictEqual(tags, ["ml"]);
assert.ok(C.verdict(winnerSel).includes("ML - TF-IDF + SVM") && C.verdict(winnerSel).includes("91.2/100"));
// ties and undetermined never show a Best Response badge or verdict trophy
for (const s of [tieSel, noneSel]) {
    assert.ok(C.ARCH.every((k) => !C.cardTag(s, k).includes("Best Response")));
    assert.ok(!C.verdict(s).includes("Best Response"));
}
assert.ok(C.cardTag(tieSel, "ml").includes("fastest") && C.cardTag(tieSel, "dl") === "");
assert.strictEqual(C.bestKey(tieSel), null);
// unmeasured scores are n/a, never 0
const block = C.scoreBlock(sc({ correctness: null, unavailable: ["correctness"] }), false);
assert.ok(block.includes("unavailable") && !/<b>0<\/b>/.test(block));
assert.ok(C.scoreBlock(noneSel.scores.rule, false).includes("Not scored"));
const ch = C.chart("Safety", "h", [{ key: "rule", name: "Rule-Based", value: null }, { key: "ml", name: "ML", value: 90 }], { max: 100 });
assert.ok(ch.includes("n/a") && ch.includes("90"));
// chart marks the leader; response-time chart marks the LOWEST
assert.ok(C.chart("t", "h", [{ key: "rule", name: "a", value: 30 }, { key: "ml", name: "b", value: 5 }], { lowerBetter: true }).includes('class="lead"><span class="mc-bar-name">b'));
// model-provided text is escaped
assert.ok(!C.verdict({ ...winnerSel, winner_name: "<img src=x onerror=1>", reason: "<script>x</script>" }).includes("<img"));
// aggregate overview agrees with the backend's winner
const mk = (k, o) => ({ key: k, name: k, available: true, questions: 50, answered: 50, declined: 0, overall: o, correctness: { value: 80, n: 50 }, safety: { value: 100, n: 50, level: "Safe" }, quality: { value: 70, n: 50 }, speed: { value: 50, median_ms: 9 }, unavailable: [] });
const view = { runs: [], models: { rule: mk("rule", 70), ml: mk("ml", 85), dl: mk("dl", 60) }, best: { status: "winner", winner_key: "ml", winner_name: "ML", winner_score: 85, explanation: "e", caveats: [] } };
const html = C.overview(view, { weights: { correctness: 0.4, safety: 0.3, quality: 0.2, speed: 0.1 }, tie_margin: 2, version: "2" });
assert.strictEqual((html.match(/Best-performing</g) || []).length, 1);
assert.ok(html.includes("correctness 40%") && html.includes("Response time"));
console.log("comparison.js render tests passed");
