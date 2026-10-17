// Lightweight browser-logic check without third-party DOM or test dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'conditional-model-app.js'), 'utf8');
const startup = source.indexOf('  $("sourceRows").textContent =');
assert.ok(startup > 0, 'expected app startup boundary');
const stats = { p10: 10, p25: 20, median: 30, p75: 40, p90: 50, n: 100 };
const context = {
  window: {
    CONDITIONAL_MODEL: {
      meta: {},
      phaseMetrics: { EARLY: ['early_cs_15', 'early_deaths', 'early_team_dragons'], MID: [], LATE: [] },
      comparisonProfiles: {
        'CHAMPION_ALL_PATCH|ALL|Ashe|BOTTOM|ALL|EARLY': {
          metrics: { early_cs_15: stats, early_deaths: stats, early_team_dragons: stats },
        },
      },
    },
    MODEL_MANIFEST: { parameters: { performance_rating: { minimum_metric_samples: 20 } } },
  },
  document: { getElementById: () => ({ value: 'ALL' }) },
};
vm.runInNewContext(source.slice(0, startup) + 'globalThis.testApi = { metricPerformancePercentile, metricVerdict, matchGradeSummary }; })();', context);
const { metricPerformancePercentile, metricVerdict, matchGradeSummary } = context.testApi;
for (const [p, label] of [[75, '优秀'], [50, '合格'], [25, '欠缺'], [24.99, '垃圾']]) {
  assert.match(metricVerdict('early_cs_15', p, '你'), new RegExp(label));
}
assert.equal(metricPerformancePercentile('early_deaths', 10, stats), 90);
assert.equal(metricPerformancePercentile('early_first_gank_minute', 0, stats), null);
assert.match(metricVerdict('early_team_dragons', 5, '你'), /团队情境/);
const summary = matchGradeSummary({ champion: 'Ashe', position: 'BOTTOM', durationMin: 24, early_cs_15: 12, early_deaths: 20, early_team_dragons: 0 });
assert.match(summary, /优先复盘：15 分钟 CS 垃圾 · P13/);
assert.doesNotMatch(summary, /团队小龙 垃圾/);
assert.match(summary, /不证明输因/);
console.log('Web grade checks passed');
