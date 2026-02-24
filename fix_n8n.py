import json
import glob
import os

files = glob.glob('n8n_workflows/*_sync.json')

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tier = os.path.basename(filepath).split('_')[0]
    
    # Extract the trigger node (schedule trigger and potentially code node)
    trigger_nodes = [n for n in data['nodes'] if n['type'] in ('n8n-nodes-base.scheduleTrigger', 'n8n-nodes-base.code')]
    http_nodes = [n for n in data['nodes'] if n['type'] == 'n8n-nodes-base.httpRequest' and 'webhook' in n['parameters'].get('url', '')]
    
    if not http_nodes:
        continue
        
    trigger_sync_node = http_nodes[0]
    trigger_sync_name = trigger_sync_node['name']
    
    new_nodes = []
    new_nodes.extend(trigger_nodes)
    new_nodes.append(trigger_sync_node)
    
    # Add Wait Node
    new_nodes.append({
        'parameters': { 'amount': 2, 'unit': 'minutes' },
        'id': 'wait-node',
        'name': 'Wait 2 Mins',
        'type': 'n8n-nodes-base.wait',
        'typeVersion': 1.1,
        'position': [650, 300]
    })
    
    # Add Status Check Node
    new_nodes.append({
        'parameters': {
            'method': 'GET',
            'url': f'=' + 'http://localhost:5001/job/{{ $(' + f"'{trigger_sync_name}'" + ').item.json.job_id }}',
            'sendHeaders': True,
            'headerParameters': {
                'parameters': [
                    {'name': 'X-API-Secret', 'value': '={{$env.API_SECRET}}'}
                ]
            }
        },
        'id': 'check-status',
        'name': 'Check Status',
        'type': 'n8n-nodes-base.httpRequest',
        'typeVersion': 4.2,
        'position': [850, 300]
    })
    
    # Add If Completed Node
    new_nodes.append({
        'parameters': {
            'conditions': {
                'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict'},
                'conditions': [{'id': 'c1', 'leftValue': '={{ $json.status }}', 'rightValue': 'completed', 'operator': {'type': 'string', 'operation': 'equals'}}],
                'combinator': 'and'
            }
        },
        'id': 'if-completed',
        'name': 'If Completed',
        'type': 'n8n-nodes-base.if',
        'typeVersion': 2,
        'position': [1050, 300]
    })
    
    # Add If Error Node
    new_nodes.append({
        'parameters': {
            'conditions': {
                'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict'},
                'conditions': [{'id': 'c2', 'leftValue': '={{ $json.status }}', 'rightValue': 'error', 'operator': {'type': 'string', 'operation': 'equals'}}],
                'combinator': 'and'
            }
        },
        'id': 'if-error',
        'name': 'If Error',
        'type': 'n8n-nodes-base.if',
        'typeVersion': 2,
        'position': [1250, 450]
    })
    
    # Add Success Log
    new_nodes.append({
        'parameters': {
            'values': {'string': [{'name': 'message', 'value': f'✅ {tier.capitalize()} sync finished. Result: {{{{ JSON.stringify($json) }}}}'}]}
        },
        'id': 'success-log',
        'name': 'Success Log',
        'type': 'n8n-nodes-base.set',
        'typeVersion': 3.4,
        'position': [1250, 150]
    })
    
    # Add Error Log
    new_nodes.append({
        'parameters': {
            'values': {'string': [{'name': 'message', 'value': f'❌ {tier.capitalize()} sync failed. Error: {{{{ $json.error }}}}'}]}
        },
        'id': 'error-log',
        'name': 'Error Log',
        'type': 'n8n-nodes-base.set',
        'typeVersion': 3.4,
        'position': [1450, 350]
    })
    
    data['nodes'] = new_nodes
    
    # Connections
    conns = {}
    
    # Map the trigger nodes logic
    if len(trigger_nodes) == 1:
        conns[trigger_nodes[0]['name']] = {'main': [[{'node': trigger_sync_name, 'type': 'main', 'index': 0}]]}
    elif len(trigger_nodes) == 2:
        conns[trigger_nodes[0]['name']] = {'main': [[{'node': trigger_nodes[1]['name'], 'type': 'main', 'index': 0}]]}
        conns[trigger_nodes[1]['name']] = {'main': [[{'node': trigger_sync_name, 'type': 'main', 'index': 0}]]}
        
    conns[trigger_sync_name] = {'main': [[{'node': 'Wait 2 Mins', 'type': 'main', 'index': 0}]]}
    conns['Wait 2 Mins'] = {'main': [[{'node': 'Check Status', 'type': 'main', 'index': 0}]]}
    conns['Check Status'] = {'main': [[{'node': 'If Completed', 'type': 'main', 'index': 0}]]}
    
    conns['If Completed'] = {'main': [[{'node': 'Success Log', 'type': 'main', 'index': 0}], [{'node': 'If Error', 'type': 'main', 'index': 0}]]}
    conns['If Error'] = {'main': [[{'node': 'Error Log', 'type': 'main', 'index': 0}], [{'node': 'Wait 2 Mins', 'type': 'main', 'index': 0}]]}
    
    data['connections'] = conns
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f'Updated {filepath}')

