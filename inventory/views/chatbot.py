import os
import anthropic
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


@csrf_exempt
@require_POST
def chatbot_query(request):
    """Handle chatbot queries using Claude API"""
    try:
        data = request.json
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return JsonResponse({"error": "No message provided"}, status=400)
        
        # Get API key from settings
        api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
        if not api_key:
            return JsonResponse({"error": "Anthropic API key not configured"}, status=500)
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Create system prompt for inventory assistant
        system_prompt = """You are a helpful inventory management assistant for a pharmacy/apothecary. 
        You help users with:
- Finding information about products, categories, and suppliers
- Managing stock levels and inventory
- Providing product recommendations
- Answering questions about the inventory system
- Supporting Greek and English languages

Be concise, helpful, and professional. If you don't know something, say so honestly."""
        
        # Call Claude API
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        response_text = message.content[0].text
        
        return JsonResponse({
            "success": True,
            "response": response_text
        })
        
    except anthropic.APIError as e:
        return JsonResponse({"error": f"API error: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)
