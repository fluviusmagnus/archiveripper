# ripper.py
# Copyright (c) 2020  James Shiffer
# This file contains the main application logic.

import argparse, api, logging, os, sys, random, time

def main():
    client = api.ArchiveReaderClient()
    logging.basicConfig(level=logging.INFO)

    # Parse book id and credentials
    parser = argparse.ArgumentParser()
    parser.add_argument('id', nargs='?', 
        help='Look for the book\'s identifier (the part of the url immediately after "https://archive.org/details/").')
    parser.add_argument('-u', '--username', help='Your archive.org account\'s email.')
    parser.add_argument('-p', '--password', help='Your archive.org account\'s password')
    parser.add_argument('-a', '--all-pages', action='store_true', help='Download every page of the book')
    parser.add_argument('-r', '--page-range', help='Download pages within a range (eg. 1-15)')
    parser.add_argument('-R', '--redownload', action='store_true', help='Redownloads pages even if they\'re already on disk')
    parser.add_argument('-d', '--output-dir', help='Directory you want the pages to be written to. If undefined the directory will be named the book id')
    parser.add_argument('-s', '--scale', default=0, type=int, help='Image resolution of the pages requested, can save bandwidth if the best image quality isn\'t necessary. Higher integers mean smaller resolution, default is 0 (no downscaling)')
    args = parser.parse_args()

    id = args.id
    username = args.username
    password = args.password

    #If any of the credentials isn't specified with cmdline args ask for it interactively
    if not args.id:
        print('Look for the book\'s identifier (the part of the url immediately after "https://archive.org/details/").')
        id = input('Enter it here: ')
        logging.debug('received book ID: %s' % id)
    if not args.username:
        username = input('Enter your archive.org email: ')
    if not args.password:
        password = input('Enter your archive.org password: ')


    logging.debug('attempting login with user-supplied credentials')
    client.login(username, password)

    logging.debug('attempting to start scheduler')
    client.schedule_loan_book(id)

    if not args.output_dir:
        dir = './' + id
    else:
        dir = os.path.expanduser(args.output_dir)

    logging.debug('creating output dir "%s"' % dir)
    if os.path.isdir(dir):
        response = input('Output folder %s already exists. Continue? ' \
            % dir)
        if not response.lower().startswith('y'):
            return
    else:
        os.mkdir(dir)

    page_count = client.fetch_book_metadata()
    if not args.all_pages:
        if not args.page_range:
            print('The book is %d pages long. Which pages do you want?' % page_count)
            desired_pages = input('Enter a range (eg. 1-15) or leave blank for all: ')
        else:
            desired_pages = args.page_range
    else:
        desired_pages = ''

    if desired_pages:
        [start, end] = desired_pages.split('-')
        start = int(start) - 1
        end = int(end) - 1
    else:
        start = 0
        end = page_count
    logging.debug('planning on fetching pages %d thru %d' % (start, end))

    total = end - start

    for i in range(start, end):
        savepath='%s/%d.jpg' % (dir, i + 1)
        savepathnext='%s/%d.jpg' % (dir, i + 2)
        logging.debug('downloading page %d (index %d)' % (i + 1, i))


        #download the last saved page even if exists because writing to file could've been interrupted
        if (args.redownload or 
                (not os.path.isfile(savepath) or 
                    (os.path.isfile(savepath) and not os.path.isfile(savepathnext)))):
            contents = client.download_page(i, str(args.scale))
            open(savepath, 'wb').write(contents)
            print('%d%% (%d/%d) done' % ((i + 1) / total * 100, i + 1, total))

            #wait a little between requests otherwise they'll block us
            sleeptime=random.uniform(1,3)
            time.sleep(sleeptime)
            logging.debug('waiting %.1f sec between requests' % sleeptime)
        else:
            print('%d%% (%d/%d) already on disk, skipping' % ((i + 1) / total * 100, i + 1, total))

    print('done')
    client.return_book(id)
    sys.exit()

if __name__ == '__main__':
    main()
