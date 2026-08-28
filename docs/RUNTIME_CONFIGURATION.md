# Runtime Configuration

Copy variable names from `.env.example` into an authorized secret/configuration system;
never commit credentials. `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` identify a
future runtime. `GOOGLE_GENAI_USE_VERTEXAI` selects a future approved provider path.
Failure-library and evidence-store variables identify externally governed data locations.

Local tests are offline and require none of these values. Importing `root_agent` only builds
configuration. Model `gemini-3.5-flash` must not be invoked until credentials, budget,
privacy, safety, and smoke-test authorization are explicitly granted.
