import requests
import json
import asyncio
import httpx

GRAPHQL_ENDPOINT = "http://localhost:4000/meta-api"
HEADERS = {
    "Profile": "SystemAdmin"
}

MODEL_FILES = [
    'models/01-user.model.json',
    'models/02-address.model.json',
    'models/03-file.model.json',
    'models/04-admin.model.json',
    'models/05-institute.model.json',
    'models/06-class.model.json',
    'models/07-section.model.json',
    'models/08-hostel.schema.json',
    'models/09-student.model.json',
    'models/10-designation.json',
    'models/12-staff.model.json',
    'models/13-warden.model.json',
    'models/14-parent.model.json',
    'models/15-outing.model.json',
    'models/16-model.gatepass.json',
    'models/17-id-config.model.json'
]

PROFILES = [
    'profiles/default.profile.json',
    'profiles/admin.profile.json',
    'profiles/warden.profile.json',
    'profiles/parent.profile.json',
    'profiles/student.profile.json',
    'profiles/staff.profile.json',
]

PROFILE_PERMISSIONS = [
    'permissions/super-admin.schema.json',
    'permissions/admin.permission.json',
]

PROFILE_PERMISSIONS_DATA = []

USER_MODEL_ID = None
FILE_MODEL_ID = None
SYSTEM_ADMIN_PROFILE_ID = None

def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

async def graphql_request(client, mutation, variables):
    payload = {
        "query": mutation,
        "variables": variables
    }
    response = await client.post(GRAPHQL_ENDPOINT, json=payload, headers=HEADERS)
    result = response.json()

    if 'errors' in result:
        raise Exception(f"GraphQL error: {result['errors']}")

    return result['data']

async def create_profile_and_return_definition(client, profile_file):
    profile_data = load_json(profile_file)
    input_data = {'label': profile_data['label'], 'name': profile_data['name']}

    mutation = '''
        mutation CreateProfile($input: ProfileInput!) {
            createProfile(input: $input) {
                id,
                name
            }
        }
    '''
    result = await graphql_request(client, mutation, {"input": input_data})
    profile_id = result['createProfile']['id']
    profile_data['profile'] = profile_id  # Add the ID to the original data
    print(f"✅ Created profile {profile_data['name']} with id {profile_id}")
    return profile_data

async def handle_profiles(profiles):
    async with httpx.AsyncClient() as client:
        tasks = [create_profile_and_return_definition(client, pf) for pf in profiles]
        profile_definitions = await asyncio.gather(*tasks)
        return profile_definitions

def prepare_fields(fields, model_name, model_id):
    for field in fields:
        field['modelName'] = model_name
        field['model'] = model_id
    return fields

def is_user_model(model_name):
    return model_name.lower() in ['user', 'usermodel', 'users']

async def get_user_model_id(client):
    global USER_MODEL_ID
    if USER_MODEL_ID is None:
        variables = {"where": {"name": {"is": "User"}}}
        query = '''
            query ListModels($where: whereModelInput) {
                listModels(where: $where) {
                    docs {
                        name
                        id
                    }
                }
            }
        '''
        data = await graphql_request(client, query, variables)
        USER_MODEL_ID = data['listModels']['docs'][0]['id'] if data['listModels']['docs'] else None
    return USER_MODEL_ID

async def create_model_and_return_definition(client, model_file, profile_definitions):
    model_data = load_json(model_file)
    input_data = {'label': model_data['label'], 'name': model_data['name']}

    if 'description' in model_data:
        input_data['description'] = model_data['description']

    mutation = '''
        mutation CreateModel($input: ModelInput!) {
            createModel(input: $input) {
                id,
                name
            }
        }
    '''
    # result = await graphql_request(client, mutation, {"input": input_data})
    # model_id = result['createModel']['id']

    if is_user_model(model_data['name']):
        model_id = await get_user_model_id(client)
        print(f"🟡 Fetched existing 'User' model ID: {model_id}")
    else:
        result = await graphql_request(client, mutation, {"input": input_data})
        model_id = result['createModel']['id']
        print(f"✅ Created model {model_data['name']} with id {model_id}")

    prepared = prepare_fields(model_data.get('fields', []), model_data['name'], model_id)
    independent = [f for f in prepared if f.get('type') not in ('relationship', 'virtual')]
    dependent = [f for f in prepared if f.get('type') in ('relationship', 'virtual')]

    model_tab = model_data.get('tab_input', {})
    if model_tab:
        model_tab['model'] = model_id

    view_input = model_data.get('view_input', {})

    temp_view_field = view_input.get('view_fields', [])

    is_create_view = model_data.get('create_view', False)
    is_create_tab = model_data.get('create_tab', False)

    print(f"✅ Created model {model_data['name']} with id {model_id}")

    model_defination = {
        'model_name': model_data['name'],
        'model_id': model_id,
        'immediate_fields': independent,
        'dependent_fields': dependent,
        'create_tab': is_create_tab,
        'tab_input': model_tab,
        'create_view' : is_create_view,
        'view_fields' : temp_view_field,
        'view_input': view_input,
    }

    # for p in profile_definitions:
    #     if model_defination['model_name'] == 'User' and p['name'] == 'SystemAdmin':
    #         print(f"🟡 Skipping permission creation for 'User' model and 'SystemAdmin' profile")
    #     else:
    #         await create_permissions(client, p['name'], p['profile'], model_data['name'], model_id)

    return model_defination

async def handle_models(models, profile_definitions):
    async with httpx.AsyncClient() as client:
        tasks = [create_model_and_return_definition(client, pf, profile_definitions) for pf in models]
        model_definitions = await asyncio.gather(*tasks)
        return model_definitions

async def create_field(client, field):
    # print(f"Creating field: {field['name']} (type={field.get('type')})")
    mutation = '''
    mutation CreateModelField($input: ModelFieldInput!) {
      createModelField(input: $input) {
        id,
        name
      }
    }
    '''
    result = await graphql_request(client, mutation, {"input": field})
    print(f"✅ Field created: {result['createModelField']['name']} with id - {result['createModelField']['id']}")
    return result['createModelField']['id']
    
async def create_all_fields(client, model_definitions):
    print("\n🚀 Creating immediate fields across all models...\n")

    # Collect all immediate field creation tasks
    immediate_tasks = []
    immediate_field_refs = []
    for m in model_definitions:
        for field in m['immediate_fields']:
            immediate_tasks.append(create_field(client, field))
            immediate_field_refs.append(field)

    # Run them in parallel
    immediate_ids = await asyncio.gather(*immediate_tasks)

    # Attach IDs to the correct field
    for field, field_id in zip(immediate_field_refs, immediate_ids):
        field['field'] = field_id

    print("\n✅ Immediate fields created. Proceeding to dependent fields...\n")

    # Now do the same for dependent fields
    dependent_tasks = []
    dependent_field_refs = []
    for m in model_definitions:
        for field in m['dependent_fields']:
            dependent_tasks.append(create_field(client, field))
            dependent_field_refs.append(field)

    dependent_ids = await asyncio.gather(*dependent_tasks)

    for field, field_id in zip(dependent_field_refs, dependent_ids):
        field['field'] = field_id

    print("\n🎉 All fields created successfully.\n")

async def create_tab(client, tab_input):
    mutation = '''
    mutation CreateTab($input: TabInput!) {
      createTab(input: $input) {
        id,
        label
      }
    }
    '''
    result = await graphql_request(client, mutation, {"input": tab_input})
    print(f"✅ Tab created: {result['createTab']['label']} with id - {result['createTab']['id']}")
    return result['createTab']['id']

async def create_permissions(client, profile_name, profile_id, model_name, model_id):
    profile_permissions = [p for p in PROFILE_PERMISSIONS_DATA if p['profileName'] == profile_name]

    if not profile_permissions:
        print(f"⚠️ No permissions found for profile: {profile_name}")
        return
    
    model_permissions = [p for p in profile_permissions[0]['permissions'] if p['modelName'] == model_name]
    if not model_permissions:
        print(f"⚠️ No permissions found for model: {model_name} in profile: {profile_name}")
        return
    
    mutation = '''
        mutation CreatePermission($input: PermissionInput!) {
            createPermission(input: $input) {
                id
            }
        }
    '''
    variables = {
        "input": {
            "profile": profile_id,
            "model": model_id,
            "profileName": profile_name,
            "modelName": model_permissions[0]['modelName'],
            "create": model_permissions[0]['create'],
            "read": model_permissions[0]['read'],
            "update": model_permissions[0]['update'],
            "delete": model_permissions[0]['delete'],
            "fieldLevelAccess": model_permissions[0]['fieldLevelAccess'],
        }
    }
    result = await graphql_request(client, mutation, variables)
    print(f"✅ Permissions created for profile: {profile_name} on model: {model_name} with id - {result['createPermission']['id']}")

async def create_all_tabs(client, model_definitions):
    print("\n🚀 Creating tabs across all models...\n")

    # Collect all tab creation tasks
    tab_tasks = []
    for m in model_definitions:
        if m['create_tab']:
            tab_tasks.append(create_tab(client, m['tab_input']))

    # Run them in parallel
    tab_ids = await asyncio.gather(*tab_tasks)

    print("\n✅ Tabs created successfully.\n")

def prepare_view_fields(view_fields, model_fields, view_id):
    for view_field in view_fields:
        view_field_name = view_field['field_name']
        for model_field in model_fields:
            if view_field_name == model_field['name']:
                view_field['view'] = view_id
                view_field['field'] = model_field['field']
                del view_field['field_name']
                break
    return view_fields

async def handle_views(model_definitions):
    async with httpx.AsyncClient() as client:
        tasks = [create_view_and_return_definition(client, pf) for pf in model_definitions]
        view_definitions = await asyncio.gather(*tasks)
        return view_definitions
    
async def create_view_and_return_definition(client, view_input):

    # print(view_input)
    if not view_input['create_view']:
        print(f"⚠️ Skipping view creation for model: {view_input['model_name']}")
        return

    org_view = view_input['view_input']

    input_data = {
        'modelName': view_input['model_name'],
        'model': view_input['model_id'],
        'name': org_view['name'],
        'description': org_view['description'],
    }

    mutation = '''
    mutation CreateView($input: ViewInput!) {
      createView(input: $input) {
        id,
        name
      }
    }
    '''
    result = await graphql_request(client, mutation, {"input": input_data})
    print(f"✅ View created: {result['createView']['name']} with id - {result['createView']['id']}")
    input_data['view'] = result['createView']['id']
    input_data['view_fields'] = view_input['view_fields']
    input_data['immediate_fields'] = view_input['immediate_fields']
    input_data['dependent_fields'] = view_input['dependent_fields']

    return input_data

async def create_view_field(client, view_field):
    # print(f"Creating view field: {view_field['name']}")
    mutation = '''
    mutation CreateViewField($input: ViewFieldInput!) {
      createViewField(input: $input) {
        id
      }
    }
    '''
    variables = {"input": view_field}
    result = await graphql_request(client, mutation, variables)
    print(f"✅ View field created: with id - {result['createViewField']['id']}")

async def create_all_view_fields(client, view_definitions):
    print("\n🚀 Creating view fields across all views...\n")

    # Collect all view field creation tasks
    view_field_tasks = []
    for view_def in view_definitions:

        if not view_def:
            print(f"⚠️ Skipping view field creation")
            continue

        prepared_view_field = prepare_view_fields(view_def['view_fields'], [f for f in view_def['immediate_fields'] + view_def['dependent_fields']], view_def['view'])
        for view_field in prepared_view_field:
            # Prepare the view field with the correct model and field IDs
            view_field_tasks.append(create_view_field(client, view_field))

    # Run them in parallel
    await asyncio.gather(*view_field_tasks)

    print("\n✅ View fields created successfully.\n")

async def main_async():

    for filepath in PROFILE_PERMISSIONS:
        data = load_json(filepath)
        PROFILE_PERMISSIONS_DATA.append(data)

    async with httpx.AsyncClient() as client:
        profile_definitions = await handle_profiles(PROFILES)
        print("\n🎉 All profiles created.")

        model_definitions = await handle_models(MODEL_FILES, profile_definitions)
        print("\n🎉 All models created.")

        await create_all_fields(client, model_definitions)
        print("\n🎉 All fields created.")

        for model_def in model_definitions:
            for profile in profile_definitions:
                if model_def['model_name'] == 'User' and profile['name'] == 'SystemAdmin':
                    print(f"🟡 Skipping permission creation for 'User' model and 'SystemAdmin' profile")
                    continue
                await create_permissions(client, profile['name'], profile['profile'], model_def['model_name'], model_def['model_id'])
        print("\n🎉 All permissions created.")

        await create_all_tabs(client, model_definitions)
        print("\n🎉 All tabs created.")

        view_definations = await handle_views(model_definitions)
        print("\n🎉 All views created.")

        await create_all_view_fields(client, view_definations)
        print("\n🎉 All fields created.")
    

if __name__ == "__main__":
    asyncio.run(main_async())