if [ "$1" == "up" ];
then
  up="true"
  echo "Set links up"
else
  up="false"
  echo "Set links down"
fi  


curl http://127.0.0.1:8000/link \
  -X PUT \
  -H "Content-Type: application/json" \
  -d "{
    \"node1_name\": \"R1_0\",
    \"node2_name\": \"R0_0\",
    \"up\": ${up}
  }"

curl http://127.0.0.1:8000/link \
  -X PUT \
  -H "Content-Type: application/json" \
  -d "{
    \"node1_name\": \"R0_0\",
    \"node2_name\": \"R0_1\",
    \"up\": ${up}
  }"
curl http://127.0.0.1:8000/link \
  -X PUT \
  -H "Content-Type: application/json" \
  -d "{
    \"node1_name\": \"R0_0\",
    \"node2_name\": \"R3_0\",
    \"up\": ${up}
  }"
curl http://127.0.0.1:8000/link \
  -X PUT \
  -H "Content-Type: application/json" \
  -d "{
    \"node1_name\": \"R0_0\",
    \"node2_name\": \"R0_3\",
    \"up\": ${up}
  }"

