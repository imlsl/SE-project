"""
Extract traffic (task3) and OpenAI (task6) features from ver2's __init__.py
and insert them into main's __init__.py.
"""

import subprocess, re, os

# Get ver2's __init__.py content
import io
result = subprocess.run(['git', 'show', 'ver2:__init__.py'], capture_output=True)
ver2_text = result.stdout.decode('utf-8', errors='replace')
ver2_lines = ver2_text.split('\n')
print(f"ver2 __init__.py: {len(ver2_lines)} lines")

# Get main's __init__.py
with open('__init__.py', 'r', encoding='utf-8') as f:
    main_content = f.read()
    main_lines = main_content.split('\n')
print(f"main __init__.py: {len(main_lines)} lines")

# ================================================================
# Section 1: AI_SUPPORTED_SCENE_ACTIONS + OpenAI functions
# (insert after imports, before class definitions)
# ================================================================
# Find the insertion point: after all imports, before MainPathBuildings
target = '\n\nclass MainPathBuildings:'
insert_pos = main_content.find(target)
if insert_pos < 0:
    # Try alternative
    target = '\n\nclass SNA_OT_Store_All_Assets'
    insert_pos = main_content.find(target)

print(f"\nMainPathBuildings at position: {insert_pos}")

# Extract lines from ver2
# AI_SUPPORTED (49-61), OpenAI functions (178-393), Traffic functions (396-735), Traffic light (956-1225)
ver2_sections = {}

# Read specific line ranges from ver2
def get_lines(start, end):
    """Get lines from ver2, with bounds checking."""
    if start < 0 or end > len(ver2_lines):
        print(f"  WARNING: range {start}-{end} out of bounds (max {len(ver2_lines)})")
        return []
    # Strip leading/trailing blanks
    result = ver2_lines[start-1:end]  # 1-indexed to 0-indexed
    while result and result[0].strip() == '':
        result.pop(0)
    while result and result[-1].strip() == '':
        result.pop()
    return result

# Section A: AI_SUPPORTED_SCENE_ACTIONS (49-61)
ai_actions_block = get_lines(49, 61)
print(f"AI_SUPPORTED_SCENE_ACTIONS: {len(ai_actions_block)} lines")

# Section B: OpenAI helper functions (178-393)
# This includes: _get_ai_settings, _call_openai_responses_api, _plan_city_from_prompt,
# _fallback_city_plan, _fallback_scene_actions, _plan_scene_actions
openai_functions_block = get_lines(178, 393)
print(f"OpenAI functions: {len(openai_functions_block)} lines")

# Section C: Traffic infrastructure functions (396-735)
traffic_funcs_block = get_lines(396, 735)
print(f"Traffic functions: {len(traffic_funcs_block)} lines")

# Section D: Traffic light system (956-1225)
traffic_light_block = get_lines(956, 1225)
print(f"Traffic light system: {len(traffic_light_block)} lines")

# Section E: Traffic operators (4538-4590)
traffic_ops_block = get_lines(4538, 4590)
print(f"Traffic operators: {len(traffic_ops_block)} lines")

# Section F: City_Edit new methods (4636-4660)
edit_methods_block = get_lines(4636, 4660)
print(f"City_Edit new methods: {len(edit_methods_block)} lines")

# Section G: Check traffic light operator (5237-5260)
check_light_block = get_lines(5237, 5260)
print(f"Check traffic light operator: {len(check_light_block)} lines")

# Build the complete block to insert
insert_block = []

# AI_SUPPORTED_SCENE_ACTIONS
insert_block.extend(ai_actions_block)

# OpenAI helper functions
insert_block.extend(openai_functions_block)

# Traffic infrastructure
insert_block.extend(traffic_funcs_block)

# Traffic light system
insert_block.extend(traffic_light_block)

# Add traffic operators
insert_block.extend(traffic_ops_block)

# Add check traffic light operator
insert_block.extend(check_light_block)

# Add blank line before MainPathBuildings
insert_block.append('')

insert_text = '\n'.join(insert_block)

# Insert at the right place
new_content = main_content[:insert_pos] + '\n' + insert_text + '\n\n' + main_content[insert_pos:]

with open('__init__.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"\nInserted {len(insert_block)} lines before MainPathBuildings")

# ================================================================
# Section 2: sna_openai_api_key property (in AddonPreferences)
# ================================================================
# Find the class SNA_AddonPreferences_7CCE1 and add the property
target_pref = 'class SNA_AddonPreferences_7CCE1(bpy.types.AddonPreferences):'
pref_pos = new_content.find(target_pref)
if pref_pos > 0:
    # Find where to add the property (after bl_idname)
    bl_idname_pos = new_content.find('bl_idname', pref_pos)
    eol_pos = new_content.find('\n', bl_idname_pos)
    line_after = new_content.find('\n', eol_pos + 1)

    ai_prop = '''
    sna_openai_api_key: bpy.props.StringProperty(
        name='OpenAI API key',
        description='Used for natural language scene editing',
        default='',
        subtype='PASSWORD',
        maxlen=0
    )
'''
    # Find the draw method to add UI
    draw_pos = new_content.find('def draw(self, context)', pref_pos)

    new_content = new_content[:line_after] + ai_prop + new_content[line_after:]
    print("Added sna_openai_api_key to AddonPreferences")

    # Add UI field in draw method
    if draw_pos > 0:
        # Find a good insertion point in draw
        draw_body = new_content.find('layout', draw_pos)
        eol_draw = new_content.find('\n', draw_body)
        ui_line = '''
        col_D81F8 = layout.column()
        col_D81F8.prop(self, 'sna_openai_api_key', text='API Key', icon='KEYINGSET')
'''
        new_content = new_content[:eol_draw] + ui_line + new_content[eol_draw:]
        print("Added OpenAI API Key UI to AddonPreferences")
else:
    print("AddonPreferences not found!")

# ================================================================
# Section 3: Traffic integration in City_Generation.execute()
# ================================================================
# Find the return {"FINISHED"} in City_Generation (not City_Edit)
# Pattern: end of City_Generation.execute()
target_return = '        print(context.scene.sna_road_type)\n        print(context.scene.sna_description)\n        return {"FINISHED"}\n\n    def invoke(self, context, event):\n        return self.execute(context)\n\nclass SNA_OT_City_Edit'
traffic_integration = '''
        # --- Traffic integration ---
        try:
            scgs_unregister_traffic_light_timer()
            traffic_obj = _append_traffic_assets()
            if traffic_obj:
                path_source_obj = _find_city_road_graph_source_object()
                if path_source_obj:
                    vertices, edges = _extract_path_graph_from_object(path_source_obj)
                    if vertices and edges:
                        path_obj = _build_or_update_path_object("traffic_path_from_road", vertices, edges)
                        _bind_path_object_to_traffic(path_obj, traffic_obj)
                        scgs_register_traffic_light_timer()
                        print(f"[SCGS] Traffic integrated: {len(edges)} edges bound")
        except Exception as e:
            print(f"[SCGS] Traffic integration skipped: {e}")
'''

if target_return in new_content:
    new_content = new_content.replace(target_return, traffic_integration + '\n' + target_return)
    print("Added traffic integration in City_Generation.execute()")
else:
    print("FAILED: City_Generation return pattern not found")

# ================================================================
# Section 4: City_Edit new methods (turn_to_night, brighten_sky, etc.)
# ================================================================
# These are added by the rewrite above, but need the action dispatch in execute()
# Find City_Edit execute's function list
target_func_list = '        function_list = editfunction.get('
if target_func_list in new_content:
    # Add new dispatch entries after the existing ones
    old_dispatch = '''            elif value == 7:
                self.change_sunny_weather()'''
    new_dispatch = '''            elif value == 7:
                self.change_sunny_weather()
            elif value == 8:
                self.turn_to_night()
            elif value == 9:
                self.brighten_sky()
            elif value == 10:
                self.darken_sky()
            elif value == 11:
                self.set_street_lights(True)
            elif value == 12:
                self.set_street_lights(False)'''

    if old_dispatch in new_content:
        new_content = new_content.replace(old_dispatch, new_dispatch)
        print("Added dispatch entries in City_Edit.execute()")

# ================================================================
# Section 5: Registration
# ================================================================
# Add traffic operators registration near other registrations
target_reg = '    bpy.utils.register_class(SNA_OT_Process_AI_Instruction)\n'
new_reg = '''    bpy.utils.register_class(SNA_OT_Process_AI_Instruction)
    bpy.utils.register_class(SNA_OT_Rebind_Traffic_To_City)
    bpy.utils.register_class(SNA_OT_Raise_CarMesh_Height)
    bpy.utils.register_class(SNA_OT_Check_Traffic_Light_Source_7D3F1)'''

if target_reg in new_content:
    new_content = new_content.replace(target_reg, new_reg)
    print("Added traffic operator registrations")

# Add traffic light timer + load handler
target_handler = '    if scgs_reset_traffic_light_cycle not in bpy.app.handlers.load_post:\n        bpy.app.handlers.load_post.append(scgs_reset_traffic_light_cycle)'
handler_block = '''    if scgs_reset_traffic_light_cycle not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(scgs_reset_traffic_light_cycle)
    try:
        scgs_register_traffic_light_timer()
    except Exception:
        pass'''

if target_handler in new_content:
    new_content = new_content.replace(target_handler, handler_block)
    print("Added traffic light timer registration")

# ================================================================
# Section 6: Unregistration
# ================================================================
target_unreg = '    bpy.utils.unregister_class(SNA_OT_Process_AI_Instruction)\n'
new_unreg = '''    bpy.utils.unregister_class(SNA_OT_Process_AI_Instruction)
    bpy.utils.unregister_class(SNA_OT_Check_Traffic_Light_Source_7D3F1)
    bpy.utils.unregister_class(SNA_OT_Raise_CarMesh_Height)
    bpy.utils.unregister_class(SNA_OT_Rebind_Traffic_To_City)'''

if target_unreg in new_content:
    new_content = new_content.replace(target_unreg, new_unreg)
    print("Added traffic operator unregistrations")

# Add traffic light timer unregistration
target_unreg_timer = '    scgs_unregister_traffic_light_timer()\n    if scgs_reset_traffic_light_cycle in bpy.app.handlers.load_post:\n        bpy.app.handlers.load_post.remove(scgs_reset_traffic_light_cycle)'
if target_unreg_timer in new_content:
    print("Traffic timer unregistration already present")
else:
    # Find where to add
    target_unreg_loc = '    if SNA_OT_Generate_Ecology_9F2A1 is not None:\n        bpy.utils.unregister_class(SNA_OT_Generate_Ecology_9F2A1)'
    timer_unreg = '''    scgs_unregister_traffic_light_timer()
    if scgs_reset_traffic_light_cycle in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(scgs_reset_traffic_light_cycle)
    if SNA_OT_Generate_Ecology_9F2A1 is not None:
        bpy.utils.unregister_class(SNA_OT_Generate_Ecology_9F2A1)'''
    if target_unreg_loc in new_content:
        new_content = new_content.replace(target_unreg_loc, timer_unreg)
        print("Added traffic timer unregistration")

# ================================================================
# Section 7: New properties (sna_raise_car_z, sna_openai_*)
# ================================================================
target_props = '    bpy.types.Scene.sna_manual_edges = bpy.props.StringProperty('
# Find the complete block
prop_start = new_content.find(target_props)
if prop_start > 0:
    prop_end = new_content.find('\n    )', prop_start) + 5  # include closing
    new_props = '''    bpy.types.Scene.sna_manual_edges = bpy.props.StringProperty(
        name="Manual Edges",
        description="Manual road edges, format: (i,j),(i,j),...",
        default=""
    )
    bpy.types.Scene.sna_raise_car_z = bpy.props.FloatProperty(
        name="Raise Car Z",
        description="Vehicle height offset",
        default=0.02, min=0.0, max=1.0
    )
    bpy.types.Scene.sna_openai_api_key = bpy.props.StringProperty(
        name="OpenAI API Key",
        description="OpenAI API key",
        default="", subtype='PASSWORD'
    )
    bpy.types.Scene.sna_openai_base_url = bpy.props.StringProperty(
        name="OpenAI Base URL",
        description="OpenAI API base URL",
        default="https://api.openai.com/v1"
    )
    bpy.types.Scene.sna_openai_model = bpy.props.StringProperty(
        name="OpenAI Model",
        description="OpenAI model name",
        default="o4-mini"
    )
    bpy.types.Scene.sna_ai_status = bpy.props.StringProperty(
        name="AI Status",
        description="AI operation status",
        default=""
    )'''
    new_content = new_content[:prop_start] + new_props + new_content[prop_end:]
    print("Added new properties (sna_raise_car_z, sna_openai_*)")
else:
    print("FAILED: manual_edges property not found")

# ================================================================
# Section 8: Unregistration for new properties
# ================================================================
target_del = '    del bpy.types.Scene.sna_ai_instruction\n'
new_del = '    del bpy.types.Scene.sna_ai_instruction\n    del bpy.types.Scene.sna_raise_car_z\n    del bpy.types.Scene.sna_openai_api_key\n    del bpy.types.Scene.sna_openai_base_url\n    del bpy.types.Scene.sna_openai_model\n    del bpy.types.Scene.sna_ai_status\n'
if target_del in new_content:
    new_content = new_content.replace(target_del, new_del)
    print("Added property unregistration")

# ================================================================
# Write back
# ================================================================
with open('__init__.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

# Check syntax
import py_compile
try:
    py_compile.compile('__init__.py', doraise=True)
    print("\n=== Syntax: OK ===")
except py_compile.PyCompileError as e:
    print(f"\n=== Syntax FAILED: {e} ===")
