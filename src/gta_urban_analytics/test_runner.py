import pytest
import sys

def main():
    sys.exit(pytest.main(sys.argv[1:]))

if __name__ == "__main__":
    main()
