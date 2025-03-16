```python
import gradio as gr

def travel_agent(destination, budget, travel_dates, preferences):
    # Dummy implementation for a travel agent
    response = f"Planning your trip to {destination} with a budget of {budget}.\n"
    response += f"Travel Dates: {travel_dates}\n"
    response += f"Preferences: {preferences}\n"
    response += "We will find the best deals and get back to you soon!"
    return response

with gr.Blocks() as app:
    gr.Markdown("# Travel Agent")
    destination = gr.Textbox(label="Destination")
    budget = gr.Number(label="Budget ($)")
    travel_dates = gr.Textbox(label="Travel Dates")
    preferences = gr.Textbox(label="Preferences (e.g., beach, adventure, culture)")

    submit_button = gr.Button("Plan My Trip")
    output = gr.Textbox(label="Travel Plan")

    submit_button.click(travel_agent, inputs=[destination, budget, travel_dates, preferences], outputs=output)

app.launch()
```