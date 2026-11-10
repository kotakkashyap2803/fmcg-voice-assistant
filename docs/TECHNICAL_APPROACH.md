# FMCG Voice Assistant – Technical Approach

**Candidate:** Kashyap Anand Kotak  
**Role:** Software Developer  
**Project:** AI-Powered FMCG Retailer Voice Assistant

## 1. Project Overview

The FMCG Voice Assistant is a browser-based prototype designed to simulate interactions between an FMCG company's sales assistant and its retailers.

The application enables retailers to interact with an AI-powered assistant using voice or text. The assistant can respond to product-related queries, provide pricing and scheme information, check sample product availability, capture product interests and requested quantities, assist with order placement, and record follow-up requirements.

The system also maintains conversation history and generates a summary with an interaction outcome when a conversation is completed.

The prototype uses fictional business data and is intended to demonstrate the technical feasibility and workflow of an AI-assisted retailer interaction system.

## 2. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Frontend | React 19, TypeScript | User interface and interaction management |
| Build Tool | Vite | Frontend development and production builds |
| Styling | CSS | Responsive application interface |
| Backend | Python, Django | Business logic and application services |
| API Layer | Django REST Framework | Communication between frontend and backend |
| Database | MySQL | Persistent storage of application data |
| AI Integration | Google Gemini API | Natural language understanding and conversation summaries |
| AI Validation | Pydantic | Structured validation of AI-generated intent data |
| Authentication | JWT, Simple JWT | Application authentication |
| Voice Input | Browser Web Speech API | Speech recognition |
| Voice Output | Browser Speech Synthesis API | Spoken assistant responses |
| HTTP Communication | Axios | Frontend API requests |

## 3. System Architecture

The application follows a frontend-backend architecture with a REST API layer.

### High-Level Architecture

```text
             RETAILER
                 |
          Voice / Text Input
                 |
                 v
       React + TypeScript Frontend
                 |
          Django REST APIs
                 |
                 v
       Backend Application Layer
                 |
       +---------+----------+
       |                    |
       v                    v
  AI / Intent Service   Business Services
       |                    |
       v                    +----------------------+
  Google Gemini API         |          |           |
                            v          v           v
                         Product    Pricing &    Order /
                         Catalogue   Schemes     Follow-ups
                            |          |           |
                            +----------+-----------+
                                       |
                                       v
                                  MySQL Database
                                       |
                                       v
                              Conversation Summary
                              and Outcome Generation
                                       |
                                       v
                              Frontend Conversation
                                  History
```

### Frontend

The React application provides the interface for:

- User authentication.
- Starting and managing retailer conversations.
- Capturing voice input and providing spoken responses.
- Supporting text-based interaction as an alternative.
- Displaying product information, pricing, schemes, and order-related responses.
- Reviewing completed conversations and their summaries.

The frontend communicates with the backend through REST APIs.

### Backend

The Django backend is responsible for:

- User and retailer management.
- Product catalogue and product variant management.
- Pricing, inventory, and promotional scheme calculations.
- Conversation and message persistence.
- Capturing product interest, requested quantities, and follow-up requirements.
- Order enquiry and order processing workflows.
- Conversation completion, outcome determination, and summary generation.

The backend maintains control over business rules and calculations rather than relying on AI-generated responses for transactional decisions.

### AI Integration

Google Gemini is integrated through a dedicated intent-processing service.

The AI layer interprets natural language input and identifies relevant information such as:

- User intent.
- Product mentions.
- Requested quantities.
- Product-related questions.
- Interest or follow-up requirements.

Structured outputs are validated using Pydantic schemas before being used by the application.

The backend then executes the appropriate business logic and generates a response based on the available application data.

This approach separates natural language understanding from business-critical operations such as pricing, discount calculation, and order processing.

## 4. Core Application Modules

### 4.1 Authentication and Retailer Management

The application provides authenticated access and maintains retailer records.

Sample retailer data is used to simulate interactions with different retailers.

### 4.2 Product Catalogue

The catalogue maintains sample FMCG products, product variants, packaging sizes, and associated product information.

The assistant can respond to product discovery and product-related queries using this data.

### 4.3 Pricing, Inventory, and Schemes

The backend handles product pricing, sample inventory availability, and promotional schemes.

Eligible discounts are calculated using backend business rules. For example, a quantity-based offer can be applied when the requested quantity meets the configured slab conditions.

The assistant communicates the applicable offer and final calculated amount to the retailer.

### 4.4 Conversation and Order Management

Each interaction is associated with a conversation record.

The application stores conversation messages and captures relevant details such as product interest, requested quantities, and order information.

The order workflow uses the captured product and quantity information to process the retailer's order request.

### 4.5 Follow-up Management

The application supports capturing follow-up requirements during retailer interactions so that these requirements can be retained for subsequent action.

### 4.6 Conversation Summary and Outcome

When a conversation is completed, the backend:

1. Collects the relevant conversation details.
2. Identifies the interaction outcome using the captured business information.
3. Generates a concise conversation summary.
4. Saves the summary, outcome, and completion details.

A fallback summary mechanism is included so that the application can still generate a useful summary when AI-based summary generation is unavailable.

### 4.7 Past Interactions

A dedicated interface allows users to review previous conversations, including their messages, summaries, and outcomes.

## 5. Conversation Workflow

A typical interaction follows this sequence:

1. The user logs into the application.
2. A retailer is selected and a conversation is initiated.
3. The retailer asks a question using voice or text.
4. The frontend sends the input to the backend.
5. The intent-processing service identifies the request.
6. The backend retrieves the relevant catalogue, pricing, inventory, or scheme information.
7. Business rules are executed where required.
8. The assistant response is returned to the frontend and can be presented as text or speech.
9. Product interest, requested quantities, order details, or follow-up requirements are captured.
10. At the end of the interaction, the conversation is completed and its summary and outcome are saved.
11. The completed interaction becomes available in the Past Interactions section.

## 6. Assumptions and Scope

The following assumptions were made to keep the implementation within the scope of a working prototype:

- Product names, prices, retailers, inventory records, and promotional schemes are fictional sample data.
- The application simulates retailer interactions and is not connected to a real FMCG ERP, CRM, distributor management, or order fulfilment system.
- Product availability is based on the sample inventory stored in the application database.
- Pricing and scheme eligibility are determined by backend business rules.
- Google Gemini is used for natural language understanding and conversation summarisation.
- Browser-based speech recognition and speech synthesis are used instead of a dedicated telephony or speech infrastructure.
- Voice functionality depends on browser support and microphone permissions. Text-based interaction is available as a fallback.
- The prototype does not implement production-grade telecalling, telephony integration, or real-time human-agent escalation.
- External integrations, production deployment, enterprise-scale security controls, and high-volume concurrency are outside the current prototype scope.

## 7. Reliability and Design Considerations

Some implementation decisions were made to improve the reliability of the prototype:

- **Separation of responsibilities:** AI interpretation and deterministic business logic are handled separately.
- **Structured AI output:** Pydantic validation helps ensure that extracted intent information follows the expected schema.
- **Backend-controlled calculations:** Pricing and discount calculations are performed by the backend to avoid relying on potentially inconsistent AI-generated calculations.
- **Persistence:** Conversation details, messages, and outcomes are stored in MySQL.
- **Fallback handling:** Fallback mechanisms are included for intent processing and conversation summary generation where applicable.
- **Environment-based configuration:** Sensitive credentials and environment-specific settings are maintained through environment variables rather than committed source code.

## 8. Running the Application

The repository includes a README.md file with the prerequisites, environment configuration, database setup, dependency installation, migrations, sample data seeding, and commands to run the frontend and backend locally.

The application can be evaluated locally by following those instructions.

## 9. Future Enhancements

The following enhancements could be considered for a production-oriented implementation:

- Integration with an actual FMCG ERP, CRM, and distributor management system.
- Production-grade speech-to-text and text-to-speech services.
- Telephony integration for inbound and outbound retailer calls.
- Multilingual conversation support and regional language optimisation.
- Human-agent handoff and escalation workflows.
- Advanced analytics for retailer engagement, product demand, and order conversion.
- Role-based access control, audit logging, and enhanced security controls.
- Background processing, monitoring, and scalable deployment infrastructure.

## 10. Conclusion

The prototype demonstrates an end-to-end approach to building an AI-assisted FMCG retailer interaction system.

It combines natural language understanding, structured intent extraction, deterministic business rules, persistent conversation management, and browser-based voice interaction.

The primary design objective was to use AI where it adds value while keeping business-critical operations such as pricing, promotional calculations, and order processing controlled by the backend.