#!/usr/bin/env python3

import os
import json
import time
import shutil
import tempfile
import argparse
import requests
import datetime
import dataclasses
import pkg_resources

from bs4 import BeautifulSoup


VERSION      = pkg_resources.get_distribution("gsout").version
BASE_URL     = "https://www.gradescope.com"
USER_AGENT   = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
SEASON_ORDER = {'Spring': 0, 'Summer': 1, 'Fall': 2}


parser = argparse.ArgumentParser(
    prog="gsout",
    description="Export your gradescope submissions.",
)

def zip_file_argument(arg: str) -> str:
    if arg.endswith('.zip'):
        return arg.removesuffix(".zip")

    raise argparse.ArgumentTypeError("ZIP file path must have the .zip extension")

parser.add_argument(
    "--version", action="version",
    version=f"%(prog)s {VERSION}"
)
parser.add_argument(
    "-s", "--session", type=str, required=True,
    help="Your gradescope _gradescope_session cookie.",
)
parser.add_argument(
    "-t", "--token",   type=str, required=True,
    help="Your gradescope signed_token cookie.",
)
parser.add_argument(
    "-o", "--output",  type=zip_file_argument,
    help="Path of the ZIP archive file to create.",
    required=True,
)

args    = parser.parse_args()
session = requests.Session()
session.headers.setdefault("User-Agent",   USER_AGENT)
session.cookies.set("_gradescope_session", args.session)
session.cookies.set("signed_token",        args.token)


def list_courses() -> set[str]:
    results  = set()
    response = session.get(f"{BASE_URL}")
    webpage  = BeautifulSoup(response.text, 'html.parser')
    for class_link in webpage.find_all('a', class_='courseBox'):
        results.add(class_link['href'].split('/')[-1].strip())

    return results


@dataclasses.dataclass
class InspectedAssignmentFromCourse:
    slug:       str
    name:       str
    grade:      str
    submission: str


@dataclasses.dataclass
class InspectedCourse:
    slug:        str
    short_name:  str
    long_name:   str
    term:        str
    instructors: set[str]
    assignments: set[InspectedAssignmentFromCourse]


def inspect_course(slug: str) -> InspectedCourse:
    response = session.get(f"{BASE_URL}/courses/{slug}")
    webpage  = BeautifulSoup(response.text, 'html.parser')

    assignments = []
    for row in webpage.find('table', id='assignments-student-table').find_all('tr'):
        if row.find('a') is None:
            continue
        if row.find('div', class_='submissionStatus--score') is None:
            continue
        assignments.append(
            InspectedAssignmentFromCourse(
                slug=row.find('a')['href'].split('/')[-3].strip(),
                name=row.find('a').text.strip(),
                grade=row.find('div', class_='submissionStatus--score').text.strip(),
                submission=row.find('a')['href'].split('/')[-1].strip()
            )
        )

    return InspectedCourse(
        slug        = slug,
        short_name  = webpage.find('div', class_='sidebar--title-course').text.strip(),
        long_name   = webpage.find('div', class_='sidebar--subtitle').text.strip(),
        term        = webpage.find('h2',  class_='courseHeader--term').text.strip(),
        instructors = list({
            _.text.strip()
            for _ in webpage.find('ul', class_='js-sidebarRoster').find_all('li')
        }),
        assignments = assignments,
    )


@dataclasses.dataclass
class SubmissionFile:
    url: str
    ext: str


@dataclasses.dataclass
class InspectedSubmission:
    slug:  str
    files: list[SubmissionFile]


def list_submissions(course: InspectedCourse, assignment: InspectedAssignmentFromCourse) -> list[InspectedSubmission]:
    # TODO: Scrape the list of submissions.

    files = []
    for ext in ["pdf", "zip"]:
        files.append(SubmissionFile(
            url=f"{BASE_URL}/courses/{course.slug}/assignments/{assignment.slug}/submissions/{assignment.submission}.{ext}",
            ext=ext,
        ))

    try:
        response = session.get(f"{BASE_URL}/courses/{course.slug}/assignments/{assignment.slug}/submissions/{assignment.submission}")
        
        try:
            data = json.loads(response.text)
            link = data["pdf_attachment"]["url"]
        except:
            link = ('https://production-gradescope-uploads' + ''.join(response.text.split("https://production-gradescope-uploads")[1:])).split("&quot")[0]

        if "pdf" in link:        
            files.append(SubmissionFile(
                url=link,
                ext="pdf",
            ))
    except Exception as e:
        print(e)

    return [InspectedSubmission(
        slug=assignment.submission,
        files=files,
    )]


@dataclasses.dataclass
class DownloadedFile:
    index: str
    path:  str
    ext:   str


def download(out_dir: str, course: str, assignment: str, submission: InspectedSubmission) -> list[DownloadedFile]:
    filenames = []
    for index, link in enumerate(submission.files):
        try:
            filename = f"{course}-{assignment}-{submission.slug}-{index + 1}.{link.ext}"
            response = session.get(link.url, stream=True)
            if response.status_code != 200:
                continue

            with open(os.path.join(out_dir, filename), 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            filenames.append(DownloadedFile(
                index=index + 1,
                path=filename,
                ext=link.ext,
            ))
        except Exception as e:
            print(e)

    return filenames


def sort_courses(courses: list[InspectedCourse]) -> list[tuple[str,list[InspectedCourse]]]:
    by_term: dict = {}
    for course in courses:
        by_term[course.term] = by_term.get(course.term, []) + [course]

    def term_chrono_index(term):
        try:
            season, year = term.split()
            return (int(year), SEASON_ORDER[season])
        except Exception as e:
            print(f"Warning: Cannot sort terms. (See: {e})")

        return (0, 0)

    return [
        (term, list(courses))
        for term, courses in sorted(by_term.items(), key=lambda _: term_chrono_index(_[0]))
    ]


def main():
    print(f" henryleberre/gsout version {VERSION}\n")

    with tempfile.TemporaryDirectory(delete=False) as tmpdir:
        with open(os.path.join(tmpdir, "README.md"), "w") as readme:
            readme.write(f"""\
# Gradescope Submissions

[henryleberre/gsout](https://github.com/henryleberre/gsout) version {VERSION}
exported your gradescope submissions on {datetime.datetime.now().strftime("%Y-%m-%d at %H:%M:%S")} {time.tzname[time.daylight]}.

""")

            print("Inspecting courses:")
            courses, course_slugs = [], list_courses()
            for i, slug in enumerate(course_slugs):
                course = inspect_course(slug)
                print(f"[{str(i + 1).zfill(len(str(len(course_slugs))))}/{len(course_slugs)}] {len(course.assignments):03d} A & {len(course.instructors):03d} I. {course.short_name}.")
                courses.append(course)

            i_assignment  = 1
            n_assignments = sum([len(course.assignments) for course in courses])

            print("\nDownloading submissions:")
            for term, courses_ in sort_courses(courses):
                readme.write(f"## {term}\n\n""")

                for course in courses_:
                    readme.write(f"""\
### [{course.short_name}]({BASE_URL}/courses/{course.slug}): {course.long_name}

**Instructors:**

{'\n'.join([f'- {r}' for r in course.instructors])}

**Assignments:**
""")

                    for assignment in course.assignments:
                        print(f"[{str(i_assignment).zfill(len(str(n_assignments)))}/{n_assignments}] {course.short_name}: {assignment.name} ({assignment.grade})")

                        readme.write(f"- {assignment.name} ({assignment.grade})\n")

                        submissions = list_submissions(course, assignment)
                        for i, submission in enumerate(submissions):
                            print(f"> [{str(i + 1).zfill(len(str(len(submissions))))}/{len(submissions)}] Submission {submission.slug}")
 
                            files = download(tmpdir, course.slug, assignment.slug, submission)
                            print(f"  {len(files)} file(s) downloaded.")

                            if len(files) == 0:
                                readme.write(f"  * Submission: {submission.slug} (no files)\n")
                            else:
                                readme.write(f"  * Submission: {submission.slug} ")

                            for file in files:
                                readme.write(f"[{file.ext}-{file.index}]({file.path}) ")
                            readme.write("\n")

                            i_assignment += 1

        shutil.make_archive(args.output, 'zip', tmpdir)
