***
# TTB Alcohol Label Compliance Verifier: Automated Audit Platform
**Version 1.0 | Powered by AI Vision & Deterministic Logic**

## Product Goal (The Problem We Solve)

The **Alcohol Label Compliance Verifier** is an, end-to-end system designed to automate the complex and highly regulated auditing process for alcoholic beverage labeling required by the Alcohol and Tobacco Tax and Trade Bureau (TTB).

Its core function is to compare two distinct bodies of information:
1.  **Structured Metadata:** Application data provided in files or forms (e.g., `vintage_year`, `ABV`).
2.  **Physical Evidence:** High-resolution images of the label front and back.

This comparison generates a detailed, quantifiable **Compliance Report** that determines adherence to TTB standards and assigns a final score.

---

## Getting Started: Prerequisites & Setup

### Prerequisites Checklist (Read First!)
Before running the application, ensure you have completed these steps:
*   **Python Environment:** Python 3.8+ installed with required libraries (`requirements.txt`).
*   **AI Backend:** A local or remote AI model endpoint must be accessible and configured (e.g., LM Studio running on `http://localhost:1234/v1`).
*   **Configuration:** The `.env` file must contain valid keys for the following items.
    * `AI_BASE_URL`: the url to the LM tool like ChatGPT, Google AI, or Claude.
    * `AI_API_KEY`: The access key to the LM tool.
    * `AI_MODEL_NAME`: The specific model to use from the LM.
    * `QUICK_MODE_MAX_TOKENS`: how many tokens are allowed to use per application in quick mode.
    * `DEEP_DIVE_MAX_TOKENS`: how many tokens are allowed to use per application in deep dive mode.
    * `PDF_USER_PROMPT`: The system prompt for the PDF file scanning for applications when the scraping fails.
    * `PDF_SYSTEM_PROMPT`: The user prompt for the PDF file scanning for applications when the scraping fails.
    * `SYSTEM_PROMPT_CORE`: This is the system prompt for the label verification step.
    * `INSTRUCTIONS`: This is the instructions that appear on the page to explain how to use the app.
    * `APPLICATION_SCHEMA`: This is the schema to describe how the applications should be coming in. (Defined later)
    * `VERIFICATION_CHECKS`: This is the checks applied against the label. (Defined later)

### Installation & Launch (Developer Focus)
```bash
# Install core dependencies
pip install -r requirements.txt

# Start the Streamlit application
streamlit run app.py
```

---

## 🌐 User Guide: How to Run an Audit (Single vs. Batch Mode)

The audit process is structured into four simple steps, regardless of whether you are auditing one label or a thousand.

### **Step 1: Configure Scope**
Use the sidebar settings to define the ruleset:
*   **Select Data Format:** Choose `JSON Manifest`, `PDF Forms`, etc., based on your input files.
*   **Deep Dive Mode:** Toggle this for maximum scrutiny, activating specialized checks that are otherwise hidden.
*   **Image Processing:** Adjust contrast and size to optimize label image quality for the AI model.

### **Step 2: Provide Inputs (The Data)**
| Mode | Action | Goal |
| :--- | :--- | :--- |
| **Single App** | Enter data manually or upload one file/set of images. | Auditing a single product batch. |
| **Batch Processing** | Enable Batch Mode; upload multiple application files and all corresponding label images. | Auditing an entire portfolio of products efficiently. |

### **Step 3: Run the Audit (The Engine)**
Click **Run Verification Audit**. The system processes data through five stages to generate a result.

### **Step 4: Review Results**
A detailed `ComplianceReport` is generated, providing:
*   **Confidence Score:** A final score out of 100 points.
*   **Pass/Fail Breakdown:** For every single rule (e.g., Net Contents, Warning Text), a clear status and explanation are provided.

***

## Technical Architecture: The Audit Pipeline Deep Dive

### **1. Data Intake & Normalization (Ingestion)**
*   **Function:** Handles diverse inputs (JSON/XML files, scanned PDFs).
*   **Mechanism:** The `ingestion` adapter routes raw bytes to specialized parsers (`pdfplumber`, JSON handlers), always standardizing the result into a list of dictionaries for consistent processing.

### **2. Context & Preparation (Configuration)**
*   **Schema Building:** The system dynamically builds Pydantic schemas using all active rules (`schema_builder`). This guarantees the AI knows *exactly* what structure to return, making the output reliable.
*   **Image Prep:** Labels are processed by `image_tools` (resizing, contrast) and encoded into a base64 string array for secure transmission to the API.

### **3. Verification & Logic (The Audit Core)**
1.  **AI Inference (`vision.py`):** The AI receives all images and context under the persona of an "expert TTB compliance auditor." It extracts data *and* verifies compliance against every rule in a single pass.
2.  **Scoring Engine (`scoring.py`):** Raw findings are converted into scores. A deduction is applied for each failure based on predefined penalty points (e.g., `deduction: 30` for missing warning text).
3.  **Efficiency Loop:** The **Targeted Retesting** function isolates failures, allowing a highly focused and cost-effective re-audit only on the rules that failed initially.

### **4. System Configuration Source of Truth (Developer Focus)**

The entire logic is governed by configuration constants:

*   `APPLICATION_SCHEMA`: Defines the mandatory fields required for *any* product application record.
    *   `id`: Unique identifier used as ID/keys.
    *   `label`: User-facing text on the test.
    *   `placeholder`: The example that should be in this entry.

*   `VERIFICATION_CHECKS`: The master list of all audit rules. This includes:
    *   `id`: Unique identifier used in scoring.
    *   `label`/`description`: User-facing text and detailed regulatory requirements.
    *   `deduction`: The point penalty applied upon failure (e.g., `20`).
    *   `applicable_categories`: Controls rule visibility (e.g., only run the wine rules if `Wine` is selected).

***
## Implementation Deep Dive: Approach, Tools, and Design Decisions

This section outlines the architectural philosophy, key assumptions, and technology stack chosen to develop the TTB Label Verification App. The primary focus was on creating a **highly resilient, scalable, and user-friendly prototype** that addresses the real-world constraints of the compliance office (speed, usability for non-technical staff, and handling peak volume).

### Architectural Approach: Decomposition and Modularity

To meet the requirements for efficiency, scalability, and maintenance, the system was decomposed into four distinct, communicating layers. This modular approach ensures that a failure in one component (e.g., an image processing bug) does not crash the entire audit pipeline, maintaining the robustness required by government-level auditing.

1.  **Presentation Layer (UI/UX):** Handled by Streamlit, this layer provides the user interface for input and display. Its simplicity ensures maximum accessibility—a key requirement noted in stakeholder interviews (for users with varying technical comfort levels).
2.  **Application Ingestion Layer:** Responsible for reading diverse data inputs (JSON, PDF, XML) and normalizing them into a universal application data structure.
3.  **Core Audit Engine:** This is the heart of the system (`compliance_audit.py`). It orchestrates the entire process: connecting metadata $\rightarrow$ image prep $\rightarrow$ AI call $\rightarrow$ scoring logic.
4.  **State Management Layer (Rerunning):** By retaining and managing the state of all input data and intermediate results, the application enables the critical **Targeted Retesting** functionality, addressing efficiency concerns during peak auditing times.

### Key Assumptions & Design Constraints
These assumptions guided the design to be pragmatic while maintaining high accuracy:

1.  **Core Relationship:** The system assumes a direct relationship exists between the *application metadata* (the form) and the label image(s). The application must serve as the authoritative source that guides which labels relate to which product record.
2.  **Input Flexibility:** Recognizing the variability in physical labeling, the design accommodates multiple images per label set—whether it is a single photo containing front/back views, or multiple distinct photos.
3.  **AI Overload Mitigation:** To prevent repeating failures from overly complex scans or AI misinterpretation, the **Targeted Rerunning** mechanism was implemented. This allows the user to treat the audit as an iterative process, re-evaluating only failed checks rather than reprocessing the entire document set.

### Technology Stack (Tools Used and Justification)

| Tool / Library | Purpose in Project | Architectural Benefit |
| :--- | :--- | :--- |
| **Streamlit Framework** | Full application interface, state management, and orchestration dashboard. | Powers the entire user experience without frontend overhead. Streamlit handles responsive file ingestion (PDF manifests, form metadata, and raw image drops) and binds form configurations dynamically to underlying schemas. It heavily leverages `st.session_state` to sync reactive developer control panels and hot-reload model configuration overrides natively. |
| **Google AI Studio (Gemini API)** | Production-grade production AI vision and multimodal inference engine. | Utilized for cloud-deployed instances to host the audit platform under a free tier. By targeting Google's official OpenAI Compatibility Layer (`/v1beta/openai/`), the system swaps production targets instantly via standard environment variables (`gemini-3.5-flash`) without structural modifications to the OpenAI client core. |
| **Pydantic** | Data structure validation and consistency enforcement. | Used extensively to create explicit **data contracts** between the AI model's output and the Python application code, guaranteeing type safety regardless of the underlying API behavior. |
| **Streamlit Upload/Forms** | Handles file uploads (metadata & labels) and manual data entry. | Provides a native, intuitive UI element that aligns with user expectations for document handling. |
| **LM Studio / OpenAI SDK** | The multimodal AI backend interface. | Using an abstracted API layer allows the system to be tested quickly in a local sandbox (`LM Studio`) while remaining ready to switch to commercial APIs (OpenAI) without core code changes. |
| **Python Libraries (PIL, pdfplumber)** | Handles image preprocessing and metadata extraction from complex formats (PDFs). | Ensures that the inputs are correctly transformed into a consistent, usable format before being passed to the AI layer. |
|
### Model Testing & Optimization Notes

The initial integration utilized the **Gemma-4-e4b** model for sandbox testing. Through iterative parameter adjustment, specifically increasing the `max_tokens` limit (`DEEP_DIVE_MAX_TOKENS`), and switching from **Gemma-4-e2b** to **Gemma-4-e4b**. I observed a clear correlation: **increasing context window size and increasing model parameters reduced false negative rates**.
|
## Design Philosophy: Embracing Iterative Development (For Reviewer Context)

The inherent modularity of the system—with separate modules for ingestion, core logic, scoring, and reporting—is not merely an organizational choice; it represents a critical **deliberate design decision rooted in rapid prototyping principles.** The goal was to build a structure flexible enough to validate our hypothesis around AI capability before committing to final regulatory prompts.

### Why Modular Design Enables Iterative Prompting
The TTB compliance space involves nuanced, frequently updated regulations. Before the core logic can be finalized, we must test how specific rules are interpreted by the LLM under various conditions (e.g., "What if the label uses an abbreviation vs. full text?" or "How does the AI distinguish between a front and back view?").

By designing the application around discrete components—each rule defined by its own entry in `VERIFICATION_CHECKS` and driven by a specialized prompt (`SYSTEM_PROMPT_CORE`)—we achieved:

1.  **Isolation of Variables:** When we want to test a new interpretation (e.g., making `ABV Statement` mandatory for *all* beverage types, not just wine), we only modify the rule's entry and its associated prompt **without risking failure in other modules** (like the Warning Text or Net Contents checks).
2.  **De-Risking Prompt Finalization:** The system allows us to treat the prompts as hypotheses. We can run 10 different versions of a `SYSTEM_PROMPT_CORE` against the same label set and compare the resulting failure modes, allowing us to scientifically solidify the perfect prompt that yields consistent, reliable results before declaring the feature "final."

### The Value Proposition of Modularity
*   **High Speed Development:** It enabled extremely fast prototyping. If a rule's logic or required textual output changes, only that isolated check needs modification—the rest of the complex pipeline remains untouched.
*   **Testability and Debugging:** When an error occurs (e.g., the score is too low), the modular architecture immediately tells us if the fault lies in **(A)** Data Ingestion (Bad Input), **(B)** Prompting (AI Misinterpretation), or **(C)** Scoring Logic (Incorrect Deduction). This level of diagnostic detail is essential for a reliable compliance tool.


***

## Future Roadmap & Architectural Evolution

The next phase of development will focus entirely on **robustness, regulatory scalability, performance optimization, and enhanced model governance.** These enhancements are necessary to move from a proof-of-concept into a permanent, mission-critical operational system.

### 1. Engineering & Data Integrity Improvements (The Codebase)
These improvements address the technical limitations of the current prototype's reliance on in-memory session state and dynamic typing:

*   **Semantic Parsing over Flat Extraction:** We will evolve PDF/XML ingestion from simple "flat text-to-dict" scanners to **context-aware, deep parsers**. These modules will use sophisticated document layout analysis (e.g., recognizing tables or key-value pairs across multiple columns) to semantically map the content structure, vastly improving accuracy when dealing with complex legal documents.
*   **Static Type Hinting & Hardcoding:** To achieve maximum stability and performance, we plan to transition from dynamic Pydantic schema generation to a **hard-coded, strongly-typed validation system**. This eliminates runtime overheads associated with model building and allows for immediate compile-time error checking of the audit rules.
*   **Core Field Standardization:** A definitive set of application fields required by TTB (e.g., `bottler_name`, `appellation_of_origin`) will be standardized and type-checked at the earliest possible point in the pipeline, ensuring that all subsequent logic operates on guaranteed data quality.

### 2. Performance & Scalability Improvements
The current single-user workflow limits throughput during peak season submissions:

*   **Persistent Audit History (Database Layer):** Implementing a persistent database layer (e.g., PostgreSQL) is critical for compliance and auditing. All input files, intermediate AI outputs, raw scores, and final reports will be logged, allowing us to track the lineage of every decision.
*   **Asynchronous Batch Processing:** High-volume submissions must transition from synchronous processing. We will implement a dedicated worker queue (e.g., Celery/Redis) that processes batch uploads in the background, eliminating UI timeouts and providing users with real-time progress tracking for massive jobs.
*   **Smart Caching & State Management:** The system will leverage the audit history database to remember previously audited labels or applications. Upon re-uploading a label, the system can **automatically complete or flag checks** based on previous results that have not changed, drastically saving time and API costs.

### 3. Model Governance & User Experience (The User)
These changes make the tool easier for non-technical auditors to use and maintain:

*   **Multi-Modal AI Tiering:** We will implement a multi-model strategy:
    *   **Text Scraping Model:** A lightweight, fast model optimized *only* for rapid JSON/PDF text extraction.
    *   **Vision & Reasoning Model:** A heavy-duty model dedicated exclusively to complex visual reasoning tasks (e.g., verifying co-visibility or subtle print differences). This separates cost and performance control.
*   **Adaptive Retesting:** Implementing automatic retry logic where the system identifies checks with "marginal" confidence scores (e.g., 75% match) and prompts the user, suggesting that a second image review or minor metadata tweak might resolve the failure automatically.

---

## The Target Architecture: Service-Oriented Blueprint

The ultimate goal is to move away from a monolithic Streamlit application toward a **Microservices/Service-Oriented Architecture (SOA)**. This modular design ensures maximum decoupling and resilience.

1.  **Frontend Layer (Application UI):** Dedicated solely to the user experience, managing input, displaying results, and initiating workflow requests.
2.  **Proxy Gateway:** The central point of control. It acts as a smart router, handling all business logic before external calls. This layer manages **Rate Limiting**, **Caching Logic**, and routes requests to the correct specialized service (Heavy Model vs. Light Model).
3.  **Configuration Portal:** A fully decoupled administrative web interface. All core TTB rulesets, scoring weights (`deduction` points), system prompts, and mandatory metadata fields are managed here. This allows regulatory updates *without* requiring code deployment.
4.  **Persistent Database (Database):** The single source of truth for audit logs, history, and cached data.
5.  **Inference Engine (LM Server):** The backend LLM/Vision models remain abstracted behind the Proxy Gateway, allowing us to swap out or upgrade models without affecting the rest of the application flow.

## Configuration Management
*   **Dedicated Configuration Portal:** Abstracting all `AI_BASE_URL`, `VERIFICATION_CHECKS` definitions, and system prompts out of the `.env` file and into an administrative web interface (a "Config Portal") is mandatory for operational maturity. This allows non-developers to update rulesets without requiring code deployment or restart cycles.

### Final Goal: The Unified Experience
The ultimate goal of these improvements is to transform the tool from a powerful prototype into a seamless, enterprise workflow that feels like an integrated part of the existing TTB digital infrastructure, making the compliance agent's job faster, less error-prone, and more focused on judgment rather than data entry.
