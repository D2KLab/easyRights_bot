import yaml

def generate_yaml(path, data):
    yaml.safe_dump(data, open(path,'w'), encoding='utf-8', allow_unicode=True)

if __name__ == "__main__":
    path = "test.yml"
    data = {
        "share": "Επανεκκινήστε την εμπειρία"
    }
    generate_yaml(path, data)