import vertexai
from vertexai.generative_models import GenerativeModel

vertexai.init(
    project="devstreamai",
    location="us-central1"   # recommended region
)

model = GenerativeModel("gemini-2.5-flash")

response = model.generate_content("Say hello from Vertex AI SDK!")
print(response.text)
