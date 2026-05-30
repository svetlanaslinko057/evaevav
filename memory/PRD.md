# PRD — ATLAS DevOS / EVA-X

## Что это
Execution substrate (а не SaaS и не маркетплейс фрилансеров). Клиент описывает идею →
система генерирует scope + ценник → команда выполняет под escrow-контрактом →
QA пропускает поставку → выплаты автоматически.

## Слои

| Слой | Стек | Состояние |
|------|------|-----------|
| Backend | FastAPI · MongoDB · litellm · emergentintegrations · Stripe · WayForPay · Cloudinary · Resend | **743 endpoint**, lifespan ok, MOCK режим |
| Mobile (Expo SDK 54) | expo-router · RN 0.81 · Reanimated 4 · TypeScript | 5 ролей (admin/client/developer/tester/lead), 100 .tsx |
| Web (React 18) | CRA + craco · Tailwind · Radix · собственный design-system | 98 страниц кабинета, i18n EN+UK (1938 ключей), build готов |
| Shared | `packages/runtime-client` · `packages/design-system` | Единый клиент-рантайм |

## Бренд
Внешнее имя — **EVA-X**. Внутреннее имя кодбазы — ATLAS DevOS.

## Ключевые домены
1. **Money substrate** (запечатан) — escrow, earnings, payout, divergence observer.
2. **Payouts V2** — 22 endpoint, 4 daemon'а (worker/reaper/mock-advancer/scheduler).
3. **Acceptance / Assignment** — decision_layer, decomposition_engine, client_acceptance.
4. **Work execution** — module_execution, time_tracking, event_engine.
5. **Intelligence brains** — developer_brain, team_intelligence, revenue_brain, execution_intelligence.
6. **Admin cockpit** — 5 frozen tabs (D1 amendment 1) + read-mostly drill-downs.

## Frozen scope (`docs/product-scope-freeze.md` + amendment 1)
- **D1:** Expo admin = 5 cockpit tabs + 8 read-mostly drill-downs. Полный admin = web.
- **D2:** Expo tester = Stage 4 (4 screens). Готово.
- **D3:** Lead = conversion surface only.

## Текущее состояние (Feb 2026)
- ✅ Все три поверхности развёрнуты в Emergent workspace `/app`.
- ✅ Полный clone из `svetlanaslinko057/APPPP`.
- ✅ Boot-сидеры отработали (5 quick-login юзеров + 6 dev pool + sample-проекты).
- ✅ Аудит: `audit/AUDIT_2026-FEB_FULL_REDEPLOY_APPPP_E1_RU.md`.
- ⚠️ Известные риски: `sentence-transformers` missing, 10+ duplicate operation IDs, D1 violated (21 admin screen vs 13 frozen), pytest-asyncio blocked.

## Что дальше
См. `ROADMAP.md`. Приоритеты: i18n batch 3, Payouts V2 contract, Amendment #2, duplicate ID fix, anyio migration, Expo i18n track, Docker.
