import requests
import json

GRAPHQL_ENDPOINT = "http://localhost:4000/meta-api"
HEADERS = {
    "Profile": "SystemAdmin"
}

MODEL_FILES = [
    'institute-model.json',
    'class-model.json',
]

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


def create_field(field):
    print(f"Creating field: {field['name']} (type={field.get('type')})")
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


def main():
    
    model_definitions = []

    
    for filepath in MODEL_FILES:
        print(f"\nProcessing file: {filepath}")
        data = load_json(filepath)
        model_name = data['name']
        model_id = create_model(data)

        prepared = prepare_fields(data.get('fields', []), model_name, model_id)
        immediate = [f for f in prepared if f.get('type') not in ('relationship', 'virtual')]
        dependent = [f for f in prepared if f.get('type') in ('relationship', 'virtual')]

        model_definitions.append({
            'model_name': model_name,
            'model_id': model_id,
            'immediate_fields': immediate,
            'dependent_fields': dependent
        })

    print("\nCreating immediate fields across all models...\n")
    for m in model_definitions:
        for field in m['immediate_fields']:
            create_field(field)

    print("\nCreating dependent relationship/virtual fields...\n")
    for m in model_definitions:
        for field in m['dependent_fields']:
            create_field(field)

if __name__ == "__main__":
    main()
