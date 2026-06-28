# LangSmith Observability Setup Guide

LangSmith has been integrated to provide comprehensive observability for your technical support agent system.

## Features Added

✅ **Distributed Tracing** - Track execution flow across all agents  
✅ **Performance Monitoring** - Measure latency for each agent call  
✅ **Input/Output Logging** - Capture questions, answers, and sources  
✅ **Error Tracking** - Monitor failures and exceptions  
✅ **Agent Analytics** - Analyze orchestrator, researcher, and reviewer performance  

## Configuration

### 1. Get LangSmith API Key

1. Go to [LangSmith](https://smith.langchain.com/)
2. Sign up or log in
3. Navigate to Settings → API Keys
4. Create a new API key

### 2. Set Environment Variables

Add to your Cloud Run service:

```bash
gcloud run services update technical-support-backend \
  --region us-central1 \
  --set-env-vars "LANGSMITH_TRACING=true,LANGSMITH_PROJECT=technical-support" \
  --update-secrets "LANGSMITH_API_KEY=langsmith-api-key:latest"
```

Or for local development, add to `.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-api-key-here
LANGSMITH_PROJECT=technical-support
```

### 3. Create Secret for API Key

```bash
# Create secret
echo -n "your-langsmith-api-key" | gcloud secrets create langsmith-api-key \
  --data-file=- \
  --project technical-support-499903

# Grant access to Cloud Run service account
PROJECT_NUM=$(gcloud projects describe technical-support-499903 --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding langsmith-api-key \
  --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## What Gets Traced

### Orchestrator Agent
- **process_query**: Main coordination flow
  - Input: User question
  - Output: Final answer with sources
  - Child traces: Researcher and Reviewer calls

### Researcher Agent
- **research**: Research orchestration
  - Combines RAG and web search
  - Synthesizes findings
- **_rag_search**: Internal document retrieval
  - ChromaDB similarity search
  - Returns: Document chunks with scores
- **_web_search**: External web search
  - Tavily API calls
  - Returns: Web results with URLs

### Reviewer Agent  
- **review**: Quality assessment
  - Evaluates accuracy and completeness
  - Returns: Improved answer with score

### API Interactions
- **Question endpoint**: Full user interaction
  - Question → Processing → Answer
  - Includes all nested agent calls
  - Metadata: session_id, source_count

## Viewing Traces

### LangSmith Dashboard

1. Go to https://smith.langchain.com/
2. Select your project: `technical-support`
3. View traces in real-time

### Trace Hierarchy

```
POST /api/question
└─ orchestrator.process_query
   ├─ researcher.research
   │  ├─ researcher._rag_search (if documents exist)
   │  └─ researcher._web_search (if RAG empty)
   └─ reviewer.review
```

### Key Metrics

- **Latency**: Time for each agent call
- **Token Usage**: LLM token consumption (when using LangChain)
- **Success Rate**: Percentage of successful calls
- **Error Rate**: Failures and exceptions
- **Source Usage**: RAG vs. web search frequency

## Verify Integration

### Check Status Endpoint

```bash
curl https://technical-support-backend-dj3yyet6da-uc.a.run.app/api/status | jq .observability
```

Expected output:
```json
{
  "enabled": true,
  "project": "technical-support",
  "api_key_set": true,
  "client_initialized": true
}
```

### Test Tracing

1. Ask a question via API or frontend
2. Check LangSmith dashboard
3. You should see a new trace appear

Example:
```bash
curl -X POST https://technical-support-backend-dj3yyet6da-uc.a.run.app/api/question \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the virtual host requirements?"}'
```

## Troubleshooting

### "LangSmith tracing disabled"

Check logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND textPayload=~'LangSmith'" \
  --limit 10 --project technical-support-499903
```

Common issues:
- `LANGSMITH_TRACING` not set to `true`
- `LANGSMITH_API_KEY` missing or invalid
- Secret not accessible by service account

### No traces appearing

1. Verify environment variables are set:
   ```bash
   gcloud run services describe technical-support-backend \
     --region us-central1 \
     --format="value(spec.template.spec.containers[0].env)"
   ```

2. Check if langsmith package is installed:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND textPayload=~'langsmith'" \
     --limit 5
   ```

3. Ensure API key has correct permissions

### Traces incomplete

- Check if async functions are properly awaited
- Verify decorator placement (should be closest to function definition)
- Check for exceptions that might interrupt tracing

## Advanced Usage

### Custom Metadata

Add custom tags to traces:

```python
from utils.tracing import LangSmithTracer

with LangSmithTracer("custom_operation", metadata={"user_id": "123"}):
    # Your code here
    pass
```

### Manual Logging

Log specific interactions:

```python
from utils.tracing import log_interaction

log_interaction(
    question="User question",
    answer="Agent answer",
    sources=[...],
    metadata={"custom_field": "value"}
)
```

## Cost Considerations

LangSmith pricing (as of 2026):
- **Free Tier**: 5,000 traces/month
- **Team**: $49/month for 50,000 traces
- **Enterprise**: Custom pricing

For this project with moderate usage:
- **Estimated traces**: ~3-5 per question (orchestrator + researcher + reviewer)
- **Monthly volume**: Depends on traffic
- **Recommendation**: Start with free tier, upgrade if needed

## Benefits for Production

1. **Debugging**: Quickly identify where failures occur
2. **Performance**: Find bottlenecks in agent chains
3. **Quality**: Monitor answer accuracy and source usage
4. **Cost**: Track LLM API usage and optimize
5. **User Experience**: Identify slow queries and improve

## Disabling Tracing

To disable (e.g., for cost savings):

```bash
gcloud run services update technical-support-backend \
  --region us-central1 \
  --update-env-vars "LANGSMITH_TRACING=false"
```

The system will work normally without tracing - it gracefully falls back to standard logging.

## Next Steps

1. ✅ Install requirements with `langsmith` package
2. ✅ Create LangSmith account and get API key
3. ✅ Create secret in Google Secret Manager
4. ✅ Update Cloud Run service with environment variables
5. ✅ Rebuild and deploy
6. ✅ Test and verify traces appear
7. 📊 Monitor and analyze agent performance
