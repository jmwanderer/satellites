curl http://127.0.0.1:8000/link \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "node1_name": "R0_0",
    "node2_name": "R1_0",
    "up": false
  }'

curl http://127.0.0.1:8000/link \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "node1_name": "R0_0",
    "node2_name": "R0_1",
    "up": false
  }'
curl http://127.0.0.1:8000/link \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{
    "node1_name": "R0_0",
    "node2_name": "R2_2",
    "up": false
  }'

