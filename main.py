import metatypes


def main():
    print("Hello from metatypes!")
    print("We are:", *metatypes.__all__, sep="\n")


if __name__ == "__main__":
    main()
