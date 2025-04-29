import requests
import json

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
]

USER_MODEL_ID = None
FILE_MODEL_ID = None
DEFAULT_PROFILE_ID = None

def create_permission(profile_name, profile_id, model_name, model_id):
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
            "modelName": model_name,
            "create": True,
            "update": True,
            "delete": True,
            "read": True,
            "fieldLevelAccess": False,
        }
    }
    data = graphql_request(mutation, variables)
    permission_id = data['createPermission']['id']
    print(f"✅ Permissions created: with id - {permission_id} for model - {model_name}")
    return permission_id

def creteate_profile(profile_data):
    global DEFAULT_PROFILE_ID
    if DEFAULT_PROFILE_ID is None:
        mutation = '''
            mutation CreateProfile($input: ProfileInput!) {
                createProfile(input: $input) {
                    id,
                    name
                }
            }
        '''
        variables = {"input": profile_data}
        data = graphql_request(mutation, variables)
        profile_id = data['createProfile']['id']
        profile_name = data['createProfile']['name']
        print(f"✅ Profile created: {profile_name} with id - {profile_id}")
        DEFAULT_PROFILE_ID = profile_id
    return DEFAULT_PROFILE_ID

def is_file_model(model_name):
    is_file_model = model_name in ['File', 'file', 'Files', 'files']
    if is_file_model:
        get_file_model_id()
    return is_file_model

def get_file_model_id():
    global FILE_MODEL_ID
    if FILE_MODEL_ID is None:

        variables = {"where": {"name" : { "is": "File" }}}

        mutation = '''
            query ListModels($where: whereModelInput) {
                listModels(where: $where) {
                    docs {
                        name
                        id
                    }
                }
            }
        '''
        data = graphql_request(mutation, variables)
        FILE_MODEL_ID = data['listModels']['docs'][0]['id'] if data['listModels']['docs'] else None
    return FILE_MODEL_ID

def get_user_model_id():
    global USER_MODEL_ID
    if USER_MODEL_ID is None:

        variables = {"where": {"name" : { "is": "User" }}}

        mutation = '''
            query ListModels($where: whereModelInput) {
                listModels(where: $where) {
                    docs {
                        name
                        id
                    }
                }
            }
        '''
        data = graphql_request(mutation, variables)
        USER_MODEL_ID = data['listModels']['docs'][0]['id'] if data['listModels']['docs'] else None
    return USER_MODEL_ID

def is_user_model(model_name):
    is_user_model = model_name in ['user', 'User', 'UserModel' 'Users', 'users']
    if is_user_model:
        get_user_model_id()
    return is_user_model

def graphql_request(mutation, variables):
    payload = {
        "query": mutation,
        "variables": variables
    }
    response = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=HEADERS)

    try:
        result = response.json()
    except ValueError:
        raise Exception(f"Invalid JSON response: {response.text}")

    # print(json.dumps(result, indent=2))

    if 'errors' in result:
        raise Exception(f"GraphQL error: {result['errors']}")

    return result['data']

def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def create_model(model_data):
    input_data = {
        "name": model_data['name'],
        "label": model_data['label']
    }
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
    variables = {"input": input_data}
    data = graphql_request(mutation, variables)
    model_id = data['createModel']['id']
    model_name = data['createModel']['name']
    print(f"✅ Model created: {model_name} with id - {model_id}")
    return model_id

def prepare_fields(fields, model_name, model_id):
    for field in fields:
        field['modelName'] = model_name
        field['model'] = model_id
    return fields

def prepare_view_fields(view_fields, view):
    for field in view_fields:
        field['view'] = view
    return view_fields

def create_field(field):
    # print(f"Creating field: {field['name']} (type={field.get('type')})")
    mutation = '''
    mutation CreateModelField($input: ModelFieldInput!) {
      createModelField(input: $input) {
        id,
        name
      }
    }
    '''
    variables = {"input": field}
    data = graphql_request(mutation, variables)
    field_id = data['createModelField']['id']
    field_name = data['createModelField']['name']
    print(f"✅ Field created: {field_name} with id - {field_id}")
    return field_id

def create_tab(tab):
    # print(f"Creating tab: {tab['name']}")
    mutation = '''
    mutation CreateTab($input: TabInput!) {
      createTab(input: $input) {
        id,
        label
      }
    }
    '''
    variables = {"input": tab}
    data = graphql_request(mutation, variables)
    tab_id = data['createTab']['id']
    tab_name = data['createTab']['label']
    print(f"✅ Tab created: {tab_name} with id - {tab_id}")
    return tab_id

def create_view(view):
    # print(f"Creating view: {view['name']}")
    mutation = '''
    mutation CreateView($input: ViewInput!) {
      createView(input: $input) {
        id,
        name
      }
    }
    '''
    variables = {"input": view}
    data = graphql_request(mutation, variables)
    view_id = data['createView']['id']
    view_name = data['createView']['name']
    print(f"✅ View created: {view_name} with id - {view_id}")
    return view_id

def create_view_fields(view_field):
    # print(f"Creating view field: {view_field['name']}")
    mutation = '''
    mutation CreateViewField($input: ViewFieldInput!) {
      createViewField(input: $input) {
        id
      }
    }
    '''
    variables = {"input": view_field}
    data = graphql_request(mutation, variables)
    view_field_id = data['createViewField']['id']
    print(f"✅ View field created: {view_field_id}")
    return view_field_id

def update_view_fields(view_fields, model_fields):
    for view_field in view_fields:
        view_field_name = view_field['field_name']
        for model_field in model_fields:
            if view_field_name == model_field['name']:
                view_field['field'] = model_field['field']
                del view_field['field_name']
                break
    return view_fields

def main():
    
    model_definitions = []

    profile_data = load_json('profiles/default.profile.json')

    print(f"\nCreating profile: {profile_data['name']}")
    creteate_profile({'label': profile_data['label'], 'name': profile_data['name']})
    
    for filepath in MODEL_FILES:
        print(f"\nProcessing file: {filepath}")
        data = load_json(filepath)
        model_name = data['name']
        is_user_mod = is_user_model(model_name)
        # is_file_mod = is_file_model(model_name)
        model_id = is_user_mod and USER_MODEL_ID or create_model(data)
        # model_id = is_user_mod and USER_MODEL_ID or is_file_mod and FILE_MODEL_ID or create_model(data)

        if is_user_mod and profile_data['name'] == 'SystemAdmin':
            print("Skipping permission creation for SystemAdmin profile")
        else:
            # print(f"Creating Permission for model: {model_name}")
            create_permission(profile_data['name'], DEFAULT_PROFILE_ID, model_name, model_id)

        prepared = prepare_fields(data.get('fields', []), model_name, model_id)
        immediate = [f for f in prepared if f.get('type') not in ('relationship', 'virtual')]
        dependent = [f for f in prepared if f.get('type') in ('relationship', 'virtual')]

        model_tab = data.get('tab_input', {})
        if model_tab:
            model_tab['model'] = model_id

        view_input = data.get('view_input', {})

        temp_view_field = view_input.get('view_fields', [])

        is_create_view = data.get('create_view', False)
        is_create_tab = data.get('create_tab', False)

        if is_create_view:
            del view_input['view_fields']

        view_id = ""
        if is_create_view:
            view_input['model'] = model_id
            view_input['modelName'] = model_name
            view_id = create_view(view_input)

        view_fields = prepare_view_fields(temp_view_field, view_id)

        model_definitions.append({
            'model_name': model_name,
            'model_id': model_id,
            'immediate_fields': immediate,
            'dependent_fields': dependent,
            'create_tab': is_create_tab,
            'tab_input': model_tab,
            'create_view' : is_create_view,
            'view_fields' : view_fields
        })

    print("\nCreating immediate fields across all models...\n")
    for m in model_definitions:
        for field in m['immediate_fields']:
            field_id = create_field(field)
            field['field'] = field_id

    print("\nCreating dependent relationship/virtual fields...\n")
    for m in model_definitions:
        for field in m['dependent_fields']:
            field_id = create_field(field)
            field['field'] = field_id

    print("\nCreating Tabs and view fields...\n")
    for m in model_definitions:
        # print(m['create_tab'])
        if m['create_tab']:
            print(f"Creating Tab for model: {m['model_name']}")
            create_tab(m['tab_input'])
        # print(m['create_view'])
        if m['create_view']:
            print(f"\nCreating View for model: {m['model_name']}")
            updated_view_fields = update_view_fields(m['view_fields'], [f for f in m['immediate_fields'] + m['dependent_fields']])
            for field in updated_view_fields:
                create_view_fields(field)

if __name__ == "__main__":
    main()
