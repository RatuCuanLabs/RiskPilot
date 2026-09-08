RiskPilot

An AI trading decision and risk-intelligence layer for Binance AgentOS.

«“RiskPilot doesn't just tell AI what to trade. It puts risk intelligence and safety between an AI decision and execution.”»

RiskPilot is a deterministic decision-and-safety layer between an AI agent and a market/execution capability layer.

It evaluates technical momentum, portfolio and leveraged risk, enforces non-overridable safety limits, simulates risk mitigation for dangerous positions, and requires explicit human confirmation before a state-changing action.

The current competition baseline is dry-run only. No live Binance order is placed.

---

Why RiskPilot?

A trading AI should not only answer:

«“What should I trade?”»

It should also understand:

«“Is it safe to act?”»

RiskPilot is designed for users who need a multifunctional, risk-aware agent layer rather than a simple indicator or signal bot.

It supports different stages of the trading journey:

- Asset & Portfolio Risk Management
  Understand how an asset or position affects portfolio risk and exposure.

- Investment & Entry Assistance
  Evaluate whether a potential investment or new position is supported by current market data and risk conditions.

- Explainable Recommendations
  Provide decisions and recommendations together with the reasons behind them, based on available market and account data.

- Risk Prevention
  Detect dangerous conditions and prevent actions that violate hard safety boundaries.

- Risk Mitigation Assistance
  When a leveraged position is already dangerous, simulate potential risk-reducing actions and identify an effective reduction before execution.

- Human-in-the-Loop Execution Safety
  Require explicit confirmation and a fresh final safety check before a state-changing action can proceed.

- Future Hedge Support
  The architecture includes a hedge evaluation interface, while full hedge optimization and selection remain outside the current Phase 1–4 baseline.

The core idea

RiskPilot is not designed to make the AI trade autonomously.

It gives the AI a risk-aware decision, safety, mitigation, confirmation, and verification layer before money-moving actions.

---

1. Current Scope: Phase 1 → Phase 4

The implemented competition baseline consists of Phase 1 through Phase 4.

There is no Phase 5 in this baseline.

Phase| What it adds
Phase 1| Momentum Engine, Decision Engine, token/amount validation, conversational trade state machine, dry-run order executor
Phase 1.5| Hard safety checks, 20%-of-total-capital allocation limit, portfolio snapshots, projected exposure, structured trade results, HOLD override flow
Phase 2| Leveraged risk handling for Margin, USDⓈ-M Futures, and COIN-M Futures
Phase 3| Risk Mitigation Engine — simulates risk-reducing actions and recommends the smallest effective reduction
Phase 4| Connects mitigation to confirmation, final safety checking, dry-run execution, and verification

---

2. Architecture

                    ┌─────────────────┐
                    │       Claude       │
                    │ Conversational AI  │
                    └────────┬────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │    Binance AgentOS  │
                    │ Market / Account /  │
                    │ Execution Interfaces│
                    └────────┬─────────┘
                               │
                               ▼
              ┌────────────────────────────┐
              │           RiskPilot             │
              │                                 │
              │  Momentum Engine                │
              │        ↓                        │
              │  Decision Engine                │
              │        ↓                        │
              │  Risk & Safety Layer            │
              │        ↓                        │
              │  Mitigation Engine              │
              │        ↓                        │
              │  Confirmation                   │
              │        ↓                        │
              │  Final Safety Check             │
              │        ↓                        │
              │  DryRunOrderExecutor            │
              │        ↓                        │
              │  Verification                   │
              └─────────────┬──────────────┘
                               │
                               ▼
                       Human confirmation
                               │
                               ▼
                         Dry-run only

The responsibilities are intentionally separated:

Claude
→ understands user intent and manages the conversation

AgentOS
→ provides market, account and execution capabilities/interfaces

RiskPilot
→ evaluates momentum, risk, safety and mitigation

Human
→ confirms state-changing actions

---

3. Momentum Analysis — Phase 1

RiskPilot evaluates the latest closed 1H candle using four independent conditions:

- RSI(14) > 50
- MACD line(12,26,9) > MACD signal
- KDJ K(9,3,3) > D
- Current volume > 20-period average volume

Momentum scoring

Conditions fulfilled| Momentum
4/4| PLATINUM
3/4| GOLD
2/4| SILVER
0–1/4| WAIT/HOLD

The score is combination-agnostic: any 3 of 4 conditions produces GOLD, and any 2 of 4 produces SILVER.

---

4. Decision Engine — Phase 1

RiskPilot produces three canonical decisions:

- "EXECUTE"
- "BUY WITH NOTE"
- "WAIT/HOLD"

Momentum| Risk| Decision
PLATINUM (4/4)| LOW| "EXECUTE"
GOLD (3/4)| LOW| "BUY WITH NOTE"
SILVER (2/4)| LOW| "WAIT/HOLD"
0–1/4| LOW| "WAIT/HOLD"
Any| HIGH| "WAIT/HOLD"
Any| MEDIUM| "WAIT/HOLD"

Risk takes precedence over momentum.

A strong momentum score does not automatically mean a trade is safe.

---

5. Portfolio & Allocation Safety — Phase 1.5

Before a trade proceeds, RiskPilot evaluates portfolio state and allocation.

Hard allocation limit

Maximum allocation: 20% of total trading capital.

This is calculated against total trading capital, not merely the currently available USDT.

Example:

Total trading capital:   $100
Already deployed:         $80
Available:                $20
New allocation:            $20

Allocation = $20 / $100 = 20%

RiskPilot also calculates projected post-trade exposure.

Portfolio snapshots are fetched on demand:

1. During analysis
2. Freshly immediately before execution

There is no continuous or background portfolio monitoring in this baseline.

---

6. Hard Safety Boundary

RiskPilot separates ordinary risk recommendations from non-overridable hard safety blocks.

«HIGH risk is not automatically the same thing as a hard block.»

"HIGH" risk causes the Decision Engine to recommend "WAIT/HOLD".

A hard block is stricter and prevents the action from proceeding.

Hard safety conditions include:

- Insufficient available balance
- Invalid order
- Unsupported symbol
- Minimum-order or precision violation
- Exceeding the explicit 20%-of-total-capital allocation limit
- An explicit hard post-trade exposure limit, where defined
- "CRITICAL" leveraged margin/liquidation risk
- Required leveraged-risk data being unavailable and therefore classified as "UNKNOWN"

A hard block cannot be bypassed with a “trading anyway?” confirmation.

---

7. Leveraged Risk Handling — Phase 2

RiskPilot supports risk handling for:

- "MARGIN_SPOT"
- "USD_M_FUTURES"
- "COIN_M_FUTURES"

Risk status is supplied by an external provider interface.

RiskPilot does not invent a liquidation formula, maintenance-margin formula, or margin-ratio-to-risk mapping in this baseline.

If required risk classification is unavailable, it becomes "UNKNOWN" rather than being guessed.

Hard safety rules

CRITICAL + OPEN/ADD
→ HARD BLOCK

UNKNOWN + OPEN/ADD
→ HARD BLOCK

HEDGE with unknown post-trade risk
→ HARD BLOCK

CRITICAL + REDUCE/CLOSE
→ ALLOWED

SPOT
→ NOT_APPLICABLE

A "PLATINUM" momentum score cannot bypass a leveraged "CRITICAL" or "UNKNOWN" hard block.

Risk safety remains independent of momentum.

---

8. Risk Mitigation — Phase 3

The killer feature

RiskPilot does not stop at:

«“This position is dangerous.”»

It can also simulate:

«“What is the smallest risk-reducing action that could help?”»

The Mitigation Engine:

1. Detects a dangerous leveraged position.
2. Generates candidate reduction sizes.
3. Simulates the projected risk for each candidate.
4. Selects the smallest candidate that strictly improves the risk state.
5. Returns a mitigation recommendation rather than executing it.

If no candidate improves the risk state, RiskPilot returns:

"NO_EFFECTIVE_MITIGATION"

A hedge is not automatically assumed to be safer. Hedge evaluation remains "UNSUPPORTED" in this baseline.

Verified demonstration scenario

Position:          0.10 BTC
Current risk:      CRITICAL

Recommended action:
PARTIAL_CLOSE

Proposed reduction:
0.04 BTC

Projected risk:
CRITICAL → WARNING

Phase 2 TradeIntent:
REDUCE

Execution performed:
False

No live Binance order was sent.

The 0.04 BTC recommendation is produced by the verified mitigation candidate simulation.

---

9. Confirmation Boundary — Phase 4

A mitigation recommendation does not automatically execute.

The action must pass the complete safety boundary:

Risk Mitigation Recommendation
              ↓
      TradeIntent.REDUCE
              ↓
    Explicit User Confirmation
              ↓
     Fresh Final Safety Check
              ↓
       DryRunOrderExecutor
              ↓
          Verification

Dedicated integration tests prove that:

- A recommendation alone never invokes the executor.
- Confirmation is mandatory.
- Skipping confirmation raises an error.
- Stale or duplicate confirmation is rejected.
- "OPEN" under "CRITICAL" risk reaches "BLOCKED".
- "REDUCE" under the same "CRITICAL" state can proceed.
- Execution remains dry-run.
- The resulting execution reports "status="SIMULATED"" and "is_live=False".

The confirmation boundary is enforced by code, not merely described in the README.

---

10. Underlying Portfolio Risk Foundation

RiskPilot also contains the underlying portfolio-risk foundation used by the project.

Its existing workflow includes:

Risk Audit
    ↓
Stress Test
    ↓
Rebalance Proposal
    ↓
Confirmation
    ↓
Dry-run Execution
    ↓
Verification

The portfolio concentration model classifies exposure as:

Concentration| Risk
< 30%| LOW
30–50%| MEDIUM
≥ 50%| HIGH

The foundation also provides stress testing, rebalance proposals, execution verification, and explainability through its WHY/reporting layer.

The Phase 1–4 trading layer builds on this foundation without turning it into a live autonomous trading system.

---

11. Testing

The complete verified test suite is:

PYTHONPATH=app python -m unittest discover -s tests -p "test*.py"

Current status

222/222 tests passing

The project uses Python's built-in "unittest" framework.

Component| Tests
Underlying portfolio-risk foundation| 45
Phase 1| 73
Phase 1.5| 33
Phase 2| 35
Phase 3| 18
Phase 4| 18
Total| 222

The Phase 4 count includes mitigation-workflow integration tests and dedicated confirmation-boundary integration tests.

---

12. Dry-Run / Live Execution Boundary

This baseline is intentionally conservative.

Implemented

- Deterministic risk analysis
- Momentum analysis
- Decision logic
- Portfolio safety checks
- Leveraged-risk safety boundary
- Risk mitigation simulation
- Human confirmation boundary
- Final safety check
- Dry-run execution
- Verification
- 222 automated tests

Not implemented

- Live Binance order execution
- Automated live mitigation
- Background monitoring
- Hedge optimization
- Fee/funding-aware mitigation sizing
- A real margin-ratio-to-risk formula
- Network-calling provider implementations

"DryRunOrderExecutor" is the only concrete order-execution implementation in this baseline.

It returns:

status="SIMULATED"
is_live=False

and explicitly reports that no real order was sent.

No claim in this repository should be interpreted as a live Binance trade being executed by RiskPilot.

---

13. Demo

Run the demo with:

PYTHONPATH=app python -m riskpilot.demo.run_demo

The demonstration covers the underlying risk foundation and the Phase 1–4 trading layer.

The Phase 3/4 demonstration shows:

CRITICAL leveraged position
          ↓
Risk Mitigation
          ↓
PARTIAL_CLOSE 0.04 BTC
          ↓
Projected CRITICAL → WARNING
          ↓
TradeIntent.REDUCE
          ↓
Human Confirmation
          ↓
Final Safety Check
          ↓
Dry-run Execution
          ↓
Verification

No live Binance order is sent.

---

14. Current Limitations / Future Work

The following are intentionally not implemented in the competition baseline:

- Live execution of any kind
- Automated/live mitigation execution
- Hedge optimization
- Fee/funding-aware sizing
- Real margin-ratio-to-risk-status calculation
- Continuous or background monitoring

Provider interfaces exist for capabilities such as market data, account snapshots, leveraged-risk data, and order execution, but they do not contain network-calling implementations in this baseline.

These limitations are explicit boundaries, not hidden functionality.

---

15. Technical Philosophy

RiskPilot deliberately separates AI conversation from deterministic risk decisions.

Claude
→ understands the conversation

AgentOS
→ provides capabilities and account/market access

RiskPilot
→ evaluates risk, safety and mitigation

Human
→ confirms state-changing actions

This separation is the core idea.

The AI can suggest.
RiskPilot evaluates.
Safety rules can block.
Mitigation can be simulated.
The human confirms.
Execution is verified.

---

16. Status

Competition Baseline: Phase 1 → Phase 4

- ✅ 222/222 tests passing
- ✅ Multifunctional risk-aware agent layer
- ✅ Momentum and trading decision engine
- ✅ Portfolio allocation safety
- ✅ Leveraged-risk hard safety boundary
- ✅ Risk mitigation simulation
- ✅ Confirmation boundary
- ✅ Dry-run execution
- ✅ Verification
- 🔒 Code freeze
- 🚫 No live Binance order execution

---

RiskPilot

Putting risk intelligence and safety between an AI decision and execution.