import os
import json
import anthropic
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .api import (
    api_products, api_product_detail, api_categories, api_category_detail,
    api_suppliers, api_supplier_detail, api_stock_summary
)
from django.test import RequestFactory


@csrf_exempt
@require_POST
def chatbot_query(request):
    """Handle chatbot queries using Claude API with tool-use"""
    try:
        import json
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return JsonResponse({"error": "No message provided"}, status=400)
        
        # Get API key from settings
        api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
        if not api_key:
            return JsonResponse({"error": "Anthropic API key not configured"}, status=500)
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Define tools for Claude to use
        tools = [
            {
                "name": "search_products",
                "description": "Search for products by barcode or description. Returns paginated results.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search term for barcode or product description"
                        },
                        "category_id": {
                            "type": "integer",
                            "description": "Filter by category ID (optional)"
                        },
                        "supplier_id": {
                            "type": "integer",
                            "description": "Filter by supplier ID (optional)"
                        },
                        "low_stock": {
                            "type": "boolean",
                            "description": "Filter for products with low stock (< 10)"
                        }
                    }
                }
            },
            {
                "name": "get_product",
                "description": "Get detailed information about a specific product by ID or barcode",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "Product ID or barcode"
                        }
                    },
                    "required": ["product_id"]
                }
            },
            {
                "name": "get_categories",
                "description": "Get all categories with product counts and total stock",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_category",
                "description": "Get a specific category with its products",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category_id": {
                            "type": "integer",
                            "description": "Category ID"
                        }
                    },
                    "required": ["category_id"]
                }
            },
            {
                "name": "get_suppliers",
                "description": "Get all suppliers with product counts",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_supplier",
                "description": "Get a specific supplier with its products",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "supplier_id": {
                            "type": "integer",
                            "description": "Supplier ID"
                        }
                    },
                    "required": ["supplier_id"]
                }
            },
            {
                "name": "get_stock_summary",
                "description": "Get stock summary including total products, low stock count, out of stock count, and total stock",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        
        # System prompt
        system_prompt = """You are a helpful inventory management assistant for a pharmacy/apothecary. 
You have access to tools that can retrieve real-time information from the inventory database.

Your capabilities:
- Search for products by barcode or description
- Get detailed product information
- Browse categories and their products
- View supplier information and their products
- Check stock levels and get stock summaries

When answering questions:
1. Use the appropriate tools to retrieve current data
2. Provide accurate information based on the tool results
3. If you don't find something, say so honestly
4. Support both Greek and English languages
5. Be concise but thorough
6. For product searches, use the search_products tool with relevant filters
7. For general stock questions, use get_stock_summary
8. For category/supplier questions, use the respective tools

If a user asks about something you can't answer with the available tools, explain what information you can provide instead."""

        # Call Claude API with tools
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        # Check if Claude wants to use tools
        while message.stop_reason == "tool_use":
            # Execute tool calls
            tool_results = []
            for block in message.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    
                    # Execute the tool
                    result = execute_tool(tool_name, tool_input)
                    tool_results.append({
                        "tool_use_id": block.id,
                        "output": str(result)
                    })
            
            # Send tool results back to Claude
            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4096,
                system=system_prompt,
                tools=tools,
                messages=[
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": message.content},
                    {"role": "user", "content": tool_results}
                ]
            )
        
        # Extract final response
        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text += block.text
        
        return JsonResponse({
            "success": True,
            "response": response_text
        })
        
    except anthropic.APIError as e:
        return JsonResponse({"error": f"API error: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)


def execute_tool(tool_name, tool_input):
    """Execute a tool by calling the corresponding API view directly"""
    try:
        factory = RequestFactory()
        
        if tool_name == "search_products":
            request = factory.get('/api/products', {
                "q": tool_input.get("query", ""),
                "category": tool_input.get("category_id"),
                "supplier": tool_input.get("supplier_id"),
                "low_stock": tool_input.get("low_stock", False),
                "per_page": 20
            })
            response = api_products(request)
            return json.loads(response.content.decode('utf-8'))
        
        elif tool_name == "get_product":
            product_id = tool_input.get("product_id")
            request = factory.get(f'/api/product/{product_id}')
            response = api_product_detail(request, product_id)
            return json.loads(response.content.decode('utf-8'))
        
        elif tool_name == "get_categories":
            request = factory.get('/api/categories')
            response = api_categories(request)
            return json.loads(response.content.decode('utf-8'))
        
        elif tool_name == "get_category":
            category_id = tool_input.get("category_id")
            request = factory.get(f'/api/category/{category_id}')
            response = api_category_detail(request, category_id)
            return json.loads(response.content.decode('utf-8'))
        
        elif tool_name == "get_suppliers":
            request = factory.get('/api/suppliers')
            response = api_suppliers(request)
            return json.loads(response.content.decode('utf-8'))
        
        elif tool_name == "get_supplier":
            supplier_id = tool_input.get("supplier_id")
            request = factory.get(f'/api/supplier/{supplier_id}')
            response = api_supplier_detail(request, supplier_id)
            return json.loads(response.content.decode('utf-8'))
        
        elif tool_name == "get_stock_summary":
            request = factory.get('/api/stock-summary')
            response = api_stock_summary(request)
            return json.loads(response.content.decode('utf-8'))
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        return {"error": str(e)}
