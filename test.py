from spider import Spider
import logging


def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S', )
    s = Spider()
    s.start()


if __name__ == '__main__':
    main()
