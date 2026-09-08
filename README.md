# CertifAI: Avionics Contract & Verification Synthesis Engine (ACV-SE)

[![DO-178C DAL A Compliant](https://img.shields.io/badge/DO--178C-DAL%20A%20Assisted-blue.svg)](#)
[![Python 3.11](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](#)
[![Tests: 24 passed](https://img.shields.io/badge/tests-24%20passed-success.svg)](#)
[![License](https://img.shields.io/badge/license-Proprietary-gray.svg)](#)

The **Avionics Contract & Verification Synthesis Engine (ACV-SE)** is a verification-copilot designed to bridge the gap between benchtop exploratory prototype C code (the "spike phase") and formal **DO-178C DAL A** compliance artifacts.

The engine serves as an auditing and suggestion system that extracts formal candidate Low-Level Requirements (LLRs), detects architectural and defensive omissions in prototype code against hardware constraints, and scaffolds requirements-based unit test suites (with boundary and robustness cases) for human review and formal baseline capture.

```
+-------------------------------------------------------------------------------+
| INPUTS:                                                                       |
| 1. High-Level Requirements (HLRs) & ICDs (.json / .yaml / .md)               |
| 2. Target Prototype Code (.c / .h / .s)                                       |
| 3. Hardware / Architectural Interface Constraints (Memory maps, clock specs) |
+-------------------------------------------------------------------------------+
                                      │
                                      ▼
             [ ACV-SE Core Parsing & Synthesis Pipeline ]
                                      │
          ┌───────────────────────────┴───────────────────────────┐
          ▼                                                       ▼
[ Pipeline 1: Formal LLR Synthesis ]             [ Pipeline 2: Prototype Gap Audit ]
- Contract-driven syntax (IN/OUT/POST)           - Unhandled registers / bitfields
- Traceability links to parent HLR IDs           - Missing timeout / defensive guards
- Deterministic boundary definitions             - Floating point / integer overflow risks
          │
          ▼
 [ Engineer Sign-off Baseline ] (Human-in-the-loop review)
          │
          ▼
[ Pipeline 3: Requirements-Based Test Scaffolding ]
- Normal range vectors (Nominal)
- Equivalence partition boundaries (Boundary)
- Robustness & fault injection cases (Robustness)
- Structured Unity / CMock C test harness stubs
```

---

## 1. Key Features

### Pipeline 1: Dual-Input Low-Level Requirement (LLR) Extraction
* Maps C source functions to allocated High-Level Requirements (`HLR.json`) via interface and semantic matching.
* Generates contractual shall-statements, pre-conditions, post-conditions, and boundary definitions.
* **Strict DO-178C Constraint:** Never produces procedural pseudocode; formulates contractual state transitions and invariants.
* Flags prototype functionality lacking parent HLRs as `CANDIDATE_DERIVED_REQUIREMENT` with safety rationales.
* Enforces schema conformance against `llr_candidate_schema.json`.

### Pipeline 2: Prototype Gap & Defensive Auditing Engine
* Analyzes C source code against Hardware Interface Control Documents (`icd.json`).
* Detects omissions against **DO-178C Table A-5** objectives:
  * Unbounded hardware polling loops (`while (!(REG & READY));`) without timeout watchdogs.
  * Unhandled hardware error register states (`error_mask`).
  * Missing parameter boundary assertions on function arguments.
  * Arithmetic overflow and divide-by-zero risks.
  * Missing `default` clauses in `switch` statements.
* Outputs actionable `GAP_REPORT.md` with file locations, line numbers, severity rankings, and concrete C remediation code patterns.

### Pipeline 3: Requirements-Based Test Scaffolding
* Preserves strict black-box independence by deriving test vectors **exclusively from baselined LLR text**, ignoring implementation details.
* Generates concrete test vectors across three DO-178C partitions:
  1. **Nominal (Normal Range):** In-range inputs and expected outputs.
  2. **Boundary Value:** Exact edge transitions ($X_{min}$, $X_{min}-1$, $X_{max}$, $X_{max}+1$).
  3. **Robustness & Fault Injection:** Out-of-envelope parameters and hardware timeout/fault simulations.
* Enforces schema conformance against `test_vector_schema.json`.
* Renders executable Unity/CMock C test harness stubs (`test_stubs.c`).

---

## 2. Installation & Quick Start

```bash
# Clone the repository
git clone <repo_url>
cd certifAI

# Install in editable mode with dependencies
pip install -e .
```

### Dependencies
* Python 3.9+
* `tree-sitter` & `tree-sitter-c` for C AST parsing
* `jsonschema` for DO-178C artifact schema validation
* `jinja2` for C test harness code generation
* `python-dotenv` for automatic environment variable loading
* Optional LLM SDKs: `google-genai` (Gemini), `openai`, `anthropic`

---

## 3. Environment & Configuration (`.env`)

ACV-SE supports automated environment variable loading via `python-dotenv`. An [`.env.example`](file:///.env.example) template is provided in the repository root.

### Setup Instructions

1. Copy the example file to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Configure your keys and preferences in `.env`:
   ```ini
   # ==============================================================================
   # CertifAI / ACV-SE Environment Variables
   # ==============================================================================

   # Google Gemini API Key (Required for Gemini synthesis)
   # Obtain a key at: https://aistudio.google.com/app/apikey
   GEMINI_API_KEY=your_actual_api_key_here
   GOOGLE_API_KEY=your_actual_api_key_here

   # Active LLM Provider: auto | gemini | openai | anthropic | offline
   ACV_PROVIDER=gemini

   # Model Selection (defaults to gemini-2.5-flash / Gemini 3.5 Flash)
   ACV_MODEL=gemini-2.5-flash

   # Optional Alternative Providers
   OPENAI_API_KEY=
   ANTHROPIC_API_KEY=
   ```

> [!IMPORTANT]
> `.env` is listed in [`.gitignore`](file:///.gitignore) and is never committed to Git, ensuring your API credentials remain completely private.

---

## 4. CLI Usage

The `acv` command-line interface provides three primary subcommands:

### 1. Prototype Gap Audit
Audits prototype C source code against hardware register definitions and DO-178C Table A-5 guidelines:
```bash
acv audit \
  --code examples/flight_controller/inputs/actuator_control.c \
  --icd examples/flight_controller/inputs/icd.json \
  --out examples/flight_controller/outputs/audit/GAP_REPORT.md
```

### 2. Synthesize Candidate LLRs
Extracts formal candidate LLRs matching prototype C functions with allocated HLRs:
```bash
acv synthesize-llr \
  --code examples/flight_controller/inputs/actuator_control.c \
  --header examples/flight_controller/inputs/actuator_control.h \
  --hlr examples/flight_controller/inputs/hlr.json \
  --prefix ACT \
  --out examples/flight_controller/outputs/llr_synthesis/candidates.json
```

### 3. Generate Requirements-Based Tests
Derives black-box test vectors and Unity C test harness stubs from human-baselined LLRs:
```bash
acv generate-tests \
  --llr examples/flight_controller/inputs/approved_llr.json \
  --out examples/flight_controller/outputs/test_scaffolding/test_stubs.c \
  --vectors examples/flight_controller/outputs/test_scaffolding/test_vectors.json \
  --target-header actuator_control.h \
  --prefix ACT
```

---

## 5. LLM Providers & Determinism Controls

* **Default Provider:** Automatically resolves active provider from `.env`:
  * `gemini`: Uses `google.genai` / `google.generativeai` with `GEMINI_API_KEY`.
  * `openai`: Uses `openai` with `OPENAI_API_KEY`.
  * `anthropic`: Uses `anthropic` with `ANTHROPIC_API_KEY`.
* **Temperature:** Preserves model default temperature.
* **Air-Gapped / Offline Fallback:** When running in offline or test environments with no API keys (or `--provider offline`), ACV-SE uses its deterministic rule-based synthesis and auditing engine.
* **CLI Overrides:** Override provider and model on any command via `--provider <name>` and `--model <name>`.

---

## 6. Project Layout & Git Structure

```
certifAI/
├── .env.example                       # Example environment variables template
├── .gitignore                         # Securely ignores .env, bytecode, test caches
├── pyproject.toml                     # Package definition & 'acv' console script
├── README.md                          # Engineering & certification documentation
├── acv_engine/
│   ├── cli.py                         # CLI entrypoint ('acv' command)
│   ├── config.py                      # Global settings, dotenv loader, provider config
│   ├── schemas/
│   │   ├── validator.py               # JSONSchema validation utilities
│   │   ├── hlr_schema.json            # High-Level Requirements schema
│   │   ├── llr_candidate_schema.json  # Candidate LLR schema
│   │   ├── test_vector_schema.json    # Test specification schema
│   │   └── icd_schema.json            # Hardware ICD constraints schema
│   ├── parsers/
│   │   ├── c_ast_parser.py            # Tree-sitter C AST parser
│   │   ├── hlr_parser.py              # Validates and indexes input HLRs
│   │   └── icd_parser.py              # Validates and indexes hardware ICDs
│   ├── core/
│   │   ├── llm_client.py              # Provider-agnostic LLM interface
│   │   ├── llr_synthesizer.py         # Contractual LLR synthesizer
│   │   ├── gap_auditor.py             # DO-178C Table A-5 gap auditing engine
│   │   └── test_synthesizer.py        # Requirements-based test synthesizer
│   ├── prompts/
│   │   ├── llr_prompt_template.py     # DO-178C LLR grammar system prompts
│   │   ├── gap_prompt_template.py     # Defensive programming audit prompts
│   │   └── test_prompt_template.py    # Boundary & robustness prompts
│   └── templates/
│       └── unity_c_test_stub.j2       # Jinja2 template for Unity C test harnesses
├── examples/
│   ├── flight_controller/             # Flight surface control case study
│   │   ├── inputs/                    # Input specifications & prototype code
│   │   │   ├── actuator_control.c     # Target C prototype with intentional omissions
│   │   │   ├── actuator_control.h     # C header definitions
│   │   │   ├── hlr.json               # Allocated High-Level Requirements
│   │   │   ├── icd.json               # Hardware register & bus ICD
│   │   │   └── approved_llr.json      # Baselined LLRs for test scaffolding
│   │   └── outputs/                   # Ordered ACV-SE synthesis & audit outputs
│   │       ├── audit/
│   │       │   └── GAP_REPORT.md      # DO-178C Table A-5 defensive gap audit report
│   │       ├── llr_synthesis/
│   │       │   └── candidates.json    # Candidate LLRs conforming to schema
│   │       └── test_scaffolding/
│   │           ├── test_vectors.json  # DO-178C test vector specifications
│   │           └── test_stubs.c       # Executable Unity C test harness stubs
│   └── airspeed_sensor/               # Pitot-static indicated airspeed (IAS) case study
│       ├── inputs/                    # Simple sensor inputs
│       │   ├── airspeed_sensor.c      # Pitot acquisition prototype
│       │   ├── airspeed_sensor.h      # Sensor interface header
│       │   ├── hlr.json               # Airspeed HLRs
│       │   ├── icd.json               # Pitot transducer register ICD
│       │   └── approved_llr.json      # Approved airspeed LLRs
│       └── outputs/                   # Structured synthesis outputs
│           ├── audit/
│           │   └── GAP_REPORT.md      # Table A-5 audit findings
│           ├── llr_synthesis/
│           │   └── candidates.json    # Candidate LLRs
│           └── test_scaffolding/
│               ├── test_vectors.json  # Test vector matrix
│               └── test_stubs.c       # Unity C test harness
└── tests/                             # 24 automated unit and integration tests
    ├── test_schemas.py
    ├── test_parsers.py
    ├── test_gap_auditor.py
    ├── test_llr_synthesizer.py
    ├── test_test_synthesizer.py
    ├── test_airspeed_example.py
    └── test_cli.py
```

---

## 7. Running Automated Tests

Execute the complete automated test suite with pytest:
```bash
pytest -v tests/
```
All 24 unit, schema, AST, auditing, example case study, and end-to-end CLI tests execute cleanly.
