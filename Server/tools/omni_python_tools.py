"""
Omni Python Tools — direct access to the in-editor Python interpreter.

The headline lazy-loading tool. Instead of wrapping thousands of UE APIs
as individual MCP tools, this exposes the editor's full Python surface
through one execute call. The AI gets at the `unreal` module directly.

C++ HANDLER:
- omni.python.execute -> IPythonScriptPlugin::ExecPythonCommandEx
  Returns {success, stdout, stderr, result, mode}
"""

import logging
import textwrap
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_omni_python_tools(mcp: FastMCP):
    """Register Python-execution + introspection tools with the MCP server."""

    @mcp.tool()
    def execute_python_code(
        ctx: Context,
        code: str,
        mode: str = "ExecuteFile",
    ) -> Dict[str, Any]:
        """Execute Python code inside the Unreal Editor's interpreter.

        The code runs in the editor process with full access to the `unreal`
        module. Multi-statement scripts work in "ExecuteFile" mode (default).
        For a single expression that returns a value, use "EvaluateStatement".

        Args:
            code: Python code to run. Should start with `import unreal`.
            mode: ExecuteFile | ExecuteStatement | EvaluateStatement.

        Returns:
            Dict with success, stdout, stderr, result, mode.

        Example:
            execute_python_code("import unreal; "
                                "print(unreal.SystemLibrary.get_engine_version())")
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "error": "Unreal Engine not connected"}
            response = unreal.send_command(
                "omni.python.execute",
                {"code": code, "mode": mode},
            )
            return (response or {}).get("result", response or {"success": False, "error": "No response"})
        except Exception as e:
            logger.error(f"execute_python_code failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def discover_python_module(
        ctx: Context,
        module_name: str = "unreal",
        name_filter: str = "",
        include_classes: bool = True,
        include_functions: bool = True,
        max_items: int = 200,
        case_sensitive: bool = False,
    ) -> Dict[str, Any]:
        """Inspect the contents of a Python module loaded in the editor.

        Returns the module's classes, functions, and constants — optionally
        filtered by a substring on the name. Run inside the editor via
        execute_python_code so it sees the actual loaded `unreal` module.

        Args:
            module_name: Module to inspect (default "unreal" — UE's reflection bindings).
            name_filter: Substring filter on member names. Empty = no filter.
            include_classes: Include classes in the result.
            include_functions: Include free functions / built-ins.
            max_items: Cap result size (0 = unlimited). Default 200.
            case_sensitive: Whether name_filter is case-sensitive.
        """
        script = textwrap.dedent(f'''
            import inspect, json, importlib
            module_name = {module_name!r}
            name_filter = {name_filter!r}
            include_classes = {bool(include_classes)}
            include_functions = {bool(include_functions)}
            max_items = {int(max_items)}
            case_sensitive = {bool(case_sensitive)}

            mod = importlib.import_module(module_name)
            cmp = (lambda s: s) if case_sensitive else (lambda s: s.lower())
            needle = cmp(name_filter)

            classes, functions, constants = [], [], []
            for name in dir(mod):
                if not case_sensitive:
                    if needle and needle not in name.lower(): continue
                else:
                    if needle and needle not in name: continue
                obj = getattr(mod, name, None)
                if inspect.isclass(obj):
                    if include_classes: classes.append(name)
                elif callable(obj):
                    if include_functions: functions.append(name)
                else:
                    constants.append(name)

            if max_items > 0:
                classes = classes[:max_items]
                functions = functions[:max_items]
                constants = constants[:max_items]

            print(json.dumps({{
                "module": module_name,
                "classes": classes,
                "functions": functions,
                "constants": constants,
                "counts": {{"classes": len(classes), "functions": len(functions), "constants": len(constants)}},
            }}))
        ''').strip()
        return execute_python_code(ctx, code=script, mode="ExecuteFile")

    @mcp.tool()
    def discover_python_class(
        ctx: Context,
        class_name: str,
        method_filter: str = "",
        include_inherited: bool = False,
        include_private: bool = False,
        max_methods: int = 0,
    ) -> Dict[str, Any]:
        """Introspect a class's methods, properties, and bases.

        Args:
            class_name: Fully-qualified name (e.g. "unreal.BlueprintEditorLibrary").
            method_filter: Substring filter on member names.
            include_inherited: If false, only own members; if true, walk MRO.
            include_private: Include names starting with "_".
            max_methods: Cap (0 = unlimited).
        """
        script = textwrap.dedent(f'''
            import inspect, json, importlib
            fqname = {class_name!r}
            method_filter = {method_filter!r}
            include_inherited = {bool(include_inherited)}
            include_private = {bool(include_private)}
            max_methods = {int(max_methods)}

            mod_name, _, cls_name = fqname.rpartition(".")
            if not mod_name:
                raise ValueError("class_name must be fully qualified, e.g. 'unreal.MyClass'")
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)

            members = inspect.getmembers(cls) if include_inherited else list(vars(cls).items())
            methods, properties = [], []
            for name, value in members:
                if not include_private and name.startswith("_"): continue
                if method_filter and method_filter.lower() not in name.lower(): continue
                if callable(value):
                    methods.append(name)
                else:
                    properties.append(name)
            if max_methods > 0:
                methods = methods[:max_methods]
            bases = [b.__name__ for b in cls.__mro__[1:] if b is not object]
            print(json.dumps({{
                "class": fqname,
                "bases": bases,
                "methods": methods,
                "properties": properties,
                "counts": {{"methods": len(methods), "properties": len(properties)}},
            }}))
        ''').strip()
        return execute_python_code(ctx, code=script, mode="ExecuteFile")

    @mcp.tool()
    def discover_python_function(
        ctx: Context,
        function_name: str,
    ) -> Dict[str, Any]:
        """Return the signature + docstring of a Python function.

        Args:
            function_name: Fully-qualified name (e.g. "unreal.load_asset").
        """
        script = textwrap.dedent(f'''
            import inspect, json, importlib
            fqname = {function_name!r}
            mod_name, _, fn_name = fqname.rpartition(".")
            if not mod_name:
                raise ValueError("function_name must be fully qualified")
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, fn_name)
            try:
                sig = str(inspect.signature(fn))
            except (TypeError, ValueError):
                sig = "(<signature unavailable — likely a C-bound builtin>)"
            doc = inspect.getdoc(fn) or ""
            print(json.dumps({{
                "function": fqname,
                "signature": sig,
                "doc": doc,
            }}))
        ''').strip()
        return execute_python_code(ctx, code=script, mode="ExecuteFile")

    @mcp.tool()
    def list_python_subsystems(ctx: Context) -> Dict[str, Any]:
        """List all UEditorSubsystem subclasses available via unreal.get_editor_subsystem.

        These are the standard entry points for editor automation (e.g.
        LevelEditorSubsystem, AssetEditorSubsystem, EditorActorSubsystem).
        """
        script = textwrap.dedent('''
            import unreal, json
            subsystems = []
            for name in dir(unreal):
                obj = getattr(unreal, name, None)
                try:
                    if isinstance(obj, type) and issubclass(obj, unreal.EditorSubsystem) and obj is not unreal.EditorSubsystem:
                        subsystems.append(name)
                except TypeError:
                    pass
            subsystems.sort()
            print(json.dumps({"subsystems": subsystems, "count": len(subsystems)}))
        ''').strip()
        return execute_python_code(ctx, code=script, mode="ExecuteFile")
