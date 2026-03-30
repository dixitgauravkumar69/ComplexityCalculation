from flask import Flask, request, jsonify
import ast
import javalang
import re

app = Flask(__name__)

# ------------------- Python Analyzer -------------------
class PythonComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.max_depth = 0
        self.current_depth = 0
        self.has_log = False
        self.is_recursive = False
        self.func_name = None

    def visit_FunctionDef(self, node):
        self.func_name = node.name
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == self.func_name:
            self.is_recursive = True
        self.generic_visit(node)

    def visit_For(self, node):
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_While(self, node):
        node_str = ast.dump(node)
        # Patterns for O(log n): multiplication, division, or bit shifting
        if any(x in node_str for x in ["FloorDiv", "Mult", "Div", "LShift", "RShift"]):
            self.has_log = True
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.generic_visit(node)
        self.current_depth -= 1

def analyze_python(code):
    try:
        tree = ast.parse(code)
        visitor = PythonComplexityVisitor()
        visitor.visit(tree)
        if visitor.is_recursive: return "O(2^n)"
        if visitor.max_depth == 0: return "O(1)"
        base = f"n^{visitor.max_depth}" if visitor.max_depth > 1 else "n"
        return f"O({base} log n)" if visitor.has_log else f"O({base})"
    except Exception as e:
        return f"Parse Error: {str(e)}"

# ------------------- Java Analyzer -------------------
def analyze_java(code):
    try:
        tree = javalang.parse.parse(code)
        max_d = 0
        has_log = False
        is_recursive = False
        method_name = None

        for path, node in tree:
            # Detect Method Name for Recursion
            if isinstance(node, javalang.tree.MethodDeclaration):
                method_name = node.name
            
            if isinstance(node, javalang.tree.MethodInvocation) and node.member == method_name:
                is_recursive = True

            # Loop Depth & Log patterns
            if isinstance(node, (javalang.tree.ForStatement, javalang.tree.WhileStatement)):
                # Calculate nesting depth by checking parents in 'path'
                d = sum(1 for p in path if isinstance(p, (javalang.tree.ForStatement, javalang.tree.WhileStatement))) + 1
                max_d = max(max_d, d)
                
                # Check for log patterns: i*=2, i/=2, i>>=1 etc.
                node_str = str(node)
                if any(op in node_str for op in ['*=', '/=', '<<=', '>>=', '>> 1', '/ 2', '* 2']):
                    has_log = True
        
        if is_recursive: return "O(2^n)"
        if max_d == 0: return "O(1)"
        base = f"n^{max_d}" if max_d > 1 else "n"
        return f"O({base} log n)" if has_log else f"O({base})"
    except Exception as e:
        return f"Parse Error: Make sure it's a full Java class."

# ------------------- C++ Analyzer -------------------
def analyze_cpp(code):
    # Strip comments
    code = re.sub(r'//.*|/\*.*?\*/', '', code, flags=re.DOTALL)
    
    # Simple Recursion Check
    func_match = re.search(r'\b(\w+)\s*\(.*?\)\s*\{', code)
    is_recursive = False
    if func_match:
        name = func_match.group(1)
        if len(re.findall(rf'\b{name}\s*\(', code)) > 1:
            is_recursive = True

    # Depth Tracking using keyword and brace counting
    max_d = 0
    curr_d = 0
    has_log = False
    
    lines = code.split('\n')
    for line in lines:
        if re.search(r'\b(for|while)\b', line):
            curr_d += 1
            max_d = max(max_d, curr_d)
            if any(op in line for op in ['*=', '/=', '<<=', '>>=', '>>1', '/2', '*2']):
                has_log = True
        if '}' in line and curr_d > 0:
            curr_d -= 1

    if is_recursive: return "O(2^n)"
    if max_d == 0: return "O(1)"
    base = f"n^{max_d}" if max_d > 1 else "n"
    return f"O({base} log n)" if has_log else f"O({base})"

# ------------------- Flask Routes -------------------
@app.route('/analyze', methods=['POST'])
def analyze_code():
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'error': 'No code provided'}), 400
    
    code = data.get('code', '')
    language = data.get('language', 'python').lower()

    if language == 'python':
        result = analyze_python(code)
    elif language == 'java':
        result = analyze_java(code)
    elif language in ['c++', 'cpp']:
        result = analyze_cpp(code)
    else:
        result = "Language not supported"

    return jsonify({'complexity': result, 'language': language})

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)