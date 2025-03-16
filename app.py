import os
import gradio as gr
import openai
import time
import subprocess
import sys
import traceback
from google.generativeai import GenerativeModel

# Set your API keys - you'll need to add these for the code to work
# For testing, you can uncomment and add your keys here
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

class SmolAgent:
    def __init__(self, model_choice="gpt-4o"):
        self.model_choice = model_choice
        self.history = []
        self.app_process = None
        self.temp_file = "temp_generated_app.py"
        
    def switch_model(self, model_choice):
        self.model_choice = model_choice
        return f"Model switched to {model_choice}"
        
    def generate_code(self, prompt, model_choice=None):
        """Generate code based on the prompt using the selected model"""
        if model_choice:
            self.model_choice = model_choice
            
        if self.model_choice == "gpt-4o":
            return self._generate_with_openai(prompt)
        elif self.model_choice == "gemini":
            return self._generate_with_gemini(prompt)
        else:
            return "Unsupported model choice. Please select 'gpt-4o' or 'gemini'."
            
    def _generate_with_openai(self, prompt):
        """Use OpenAI's GPT-4o to generate code"""
        try:
            openai_key = os.environ.get("OPENAI_API_KEY")
            if not openai_key:
                return "Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
                
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": """You are a helpful AI assistant that generates Python code for Gradio applications. 
                    Return ONLY the working Python code without any explanation or markdown formatting. 
                    Make sure the code has proper imports and uses port 7861 instead of the default 7860.
                    The code MUST be valid Python syntax that can run without errors.
                    Ensure all parentheses, brackets, and quotes are properly closed."""},
                    {"role": "user", "content": f"Generate a complete, working Gradio application that: {prompt}. The code must use port 7861 instead of the default port."}
                ],
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error with OpenAI API: {str(e)}"
    
    def _generate_with_gemini(self, prompt):
        """Use Google's Gemini model to generate code"""
        try:
            google_key = os.environ.get("GOOGLE_API_KEY")
            if not google_key:
                return "Error: Google API key not found. Please set the GOOGLE_API_KEY environment variable."
                
            model = GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(
                f"""
                Generate a complete, working Gradio application that: {prompt}
                
                Return ONLY the working Python code without any explanation or markdown formatting.
                Make sure the code has proper imports and uses port 7861 instead of the default 7860.
                The code MUST be valid Python syntax that can run without errors.
                Ensure all parentheses, brackets, and quotes are properly closed.
                """
            )
            return response.text
        except Exception as e:
            return f"Error with Gemini API: {str(e)}"
    
    def verify_code_syntax(self, code):
        """Check if the code has valid Python syntax"""
        try:
            compile(code, '<string>', 'exec')
            return True, "Code syntax is valid."
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
    
    def save_code(self, code, filename="generated_app.py"):
        """Save the generated code to a file"""
        try:
            with open(filename, "w") as f:
                f.write(code)
            return f"Code saved to {filename}"
        except Exception as e:
            return f"Error saving code: {str(e)}"
    
    def run_code(self, code):
        """Run the generated code in a separate process with enhanced error handling"""
        try:
            # First verify the syntax
            is_valid, syntax_message = self.verify_code_syntax(code)
            if not is_valid:
                return syntax_message
                
            # Kill any existing process
            if self.app_process and self.app_process.poll() is None:
                if os.name == 'nt':  # Windows
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.app_process.pid)])
                else:  # Unix/Linux/Mac
                    self.app_process.terminate()
                    self.app_process.wait()
                    
            # Ensure code uses the correct port
            if "app.launch()" in code:
                code = code.replace("app.launch()", "app.launch(server_port=7861)")
            elif "app.launch(" in code and "server_port" not in code:
                code = code.replace("app.launch(", "app.launch(server_port=7861, ")
                
            # Save code to the temporary file
            with open(self.temp_file, "w") as f:
                f.write(code)
            
            # Launch in a separate process with stderr captured
            self.app_process = subprocess.Popen(
                [sys.executable, self.temp_file],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True
            )
            
            # Check for immediate errors (wait a bit for the process to start)
            time.sleep(2)
            if self.app_process.poll() is not None:
                stderr = self.app_process.stderr.read()
                if stderr:
                    return f"Application failed to start: {stderr}"
                else:
                    return "Application exited immediately without error message. Check for missing dependencies."
            
            return "Application launched successfully! View it at http://localhost:7861 in your browser."
            
        except Exception as e:
            return f"Error launching application: {str(e)}\n{traceback.format_exc()}"

    def check_app_status(self):
        """Check if the generated app is running"""
        if self.app_process:
            if self.app_process.poll() is None:
                return "Generated application is running. View it at http://localhost:7861 in your browser."
            else:
                # If process has exited, try to get error info
                stderr = self.app_process.stderr.read() if hasattr(self.app_process.stderr, 'read') else ""
                return f"Application has stopped. Exit code: {self.app_process.returncode}\nError: {stderr}"
        else:
            return "No application has been launched yet."
    
    def fix_code(self, code):
        """Attempt to fix code syntax using OpenAI"""
        try:
            is_valid, syntax_message = self.verify_code_syntax(code)
            if is_valid:
                return "Code already has valid syntax. No fixes needed."
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a Python expert. Fix the syntax errors in this code WITHOUT changing its functionality. Return ONLY the fixed code."},
                    {"role": "user", "content": f"This code has syntax errors. Please fix them:\n\n{code}\n\nError: {syntax_message}"}
                ],
                temperature=0.1
            )
            
            fixed_code = response.choices[0].message.content
            is_valid, new_message = self.verify_code_syntax(fixed_code)
            
            if is_valid:
                return fixed_code
            else:
                return f"Could not fix code automatically. {new_message}"
                
        except Exception as e:
            return f"Error while trying to fix code: {str(e)}"

# Create the Gradio interface
def create_gradio_interface():
    agent = SmolAgent()
    
    with gr.Blocks(title="Smol Agent - App Generator") as app:
        gr.Markdown("# 🤖 Smol Agent - App Generator")
        gr.Markdown("Generate Gradio applications using GPT-4o or Gemini models")
        
        with gr.Row():
            with gr.Column(scale=3):
                prompt_input = gr.Textbox(
                    label="What application would you like to build?",
                    placeholder="Create a simple image classifier for cats vs dogs",
                    lines=3
                )
            with gr.Column(scale=1):
                model_choice = gr.Radio(
                    ["gpt-4o", "gemini"],
                    label="Select Model",
                    value="gpt-4o"
                )
        
        with gr.Row():
            generate_btn = gr.Button("Generate Application", variant="primary")
            clear_btn = gr.Button("Clear")
        
        code_output = gr.Code(
            label="Generated Code",
            language="python",
            lines=20
        )
        
        with gr.Row():
            save_btn = gr.Button("Save Code")
            fix_btn = gr.Button("Fix Code Syntax")
            run_btn = gr.Button("Run Code")
            check_status_btn = gr.Button("Check App Status")
        
        status_output = gr.Textbox(label="Status", interactive=False)
        
        gr.Markdown("""
        ### How to use:
        1. Enter a description of the application you want to build
        2. Click "Generate Application" to create the code
        3. If there are syntax issues, click "Fix Code Syntax"
        4. Click "Run Code" to launch the application
        5. Open http://localhost:7861 in your browser to view the generated app
        """)
        
        # Define interactions
        generate_btn.click(
            agent.generate_code,
            inputs=[prompt_input, model_choice],
            outputs=[code_output]
        )
        
        clear_btn.click(
            lambda: ("", ""),
            inputs=None,
            outputs=[prompt_input, code_output]
        )
        
        save_btn.click(
            agent.save_code,
            inputs=[code_output],
            outputs=[status_output]
        )
        
        fix_btn.click(
            agent.fix_code,
            inputs=[code_output],
            outputs=[code_output]
        )
        
        run_btn.click(
            agent.run_code,
            inputs=[code_output],
            outputs=[status_output]
        )
        
        check_status_btn.click(
            agent.check_app_status,
            inputs=None,
            outputs=[status_output]
        )
    
    return app

# Launch the app
if __name__ == "__main__":
    app = create_gradio_interface()
    app.launch()