import yaml

def generate_yaml(path, data):
    yaml.safe_dump(data, open(path,'w'), encoding='utf-8', allow_unicode=True)

if __name__ == "__main__":
    path = "test.yml"
    data = {
        "palermo": {
            "registry_office": "التسجيل في مكتب التسجيل"
        },
        "birmingham": {
            "caz": "منطقة هواء نظيفة"
        },
        "malaga": {
            "asylum_request": "طلب اللجوء"
        },
        "larissa": {
            "nationality": "شهادة الجنسية"
        }
    }
    generate_yaml(path, data)