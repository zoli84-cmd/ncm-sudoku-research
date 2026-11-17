# TMLR submission rules relevant to this paper

Access date for every source below: 2026-11-17. All quotes are verbatim from the page named in the line above them (typographic apostrophes normalised). Sources are primary only: the TMLR website (jmlr.org/tmlr), the TMLR style-file repository on GitHub, the live TMLR submission form on OpenReview (read through the public OpenReview API), and the OpenReview documentation.

## Summary

- Double-blind, open review on OpenReview. The submission PDF and any supplementary material must be anonymized; non-anonymous submissions are a clear desk-rejection case. A public, named arXiv preprint is allowed, but the submission must not link to any version that carries the author's name. TMLR says nothing explicit about public code repositories, anonymized repository links, or preregistrations (see "Unverified or not found").
- No page limit. The submission form has a "Regular" (at most 12 pages of main content, before references and appendices) and a "Long" (more than 12 pages) type. Long submissions get 4 instead of 2 weeks for reviews and are "subject to longer timescales". Appendices go after the references in the same PDF and do not count toward the 12 pages.
- The TMLR LaTeX style file and template (https://github.com/JmlrOrg/tmlr-style-file) are mandatory and must not be modified; changes to formatting, font or layout can lead to rejection without review. Default option = anonymous submission, `[accepted]` = camera-ready, `[preprint]` = de-anonymized non-TMLR version.
- LLMs may be used as assistive tools; authors are fully responsible; LLMs cannot be authors. The TMLR FAQ additionally requires that LLM use be mentioned "as a footnote on the first page".
- Supplementary material: optional, one PDF or ZIP up to 100 MB, anonymized, publicly visible during and after review; code and data are encouraged, not required. The submission PDF itself may be at most 50 MB.
- Every author needs a complete, active OpenReview profile at submission. Profiles registered with a personal (public-domain) e-mail go to moderation, which "may take up to 2 weeks"; a profile whose career history lists only "Independent Researcher" is rejected. No rule requiring authors to review was found.
- Timeline: action editor (AE) within a week, desk-reject check within a week, at least three reviewers, discussion of 2 to 4 weeks, AE decision about a week after the reviewer recommendations; TMLR "aims to deliver a final decision approximately 9 weeks after submission" for normal-length papers, with no guarantee. Decisions: accept as is, accept with minor revision, reject.
- Prior publication: arXiv and non-archival workshops are fine; any overlap with archival peer-reviewed work (published, accepted or under parallel review) is not.
- Other: CC BY 4.0 licence from the moment of submission (copyright stays with the authors); per-author yearly submission quota; form fields for competing interests and human-subjects/IRB; Broader Impact Statement required only for work with a significant risk of harm; acknowledgments and author contributions only after acceptance.
- In 2024 and 2025 TMLR paused new submissions from 2 December to early January; no announcement for 2026 was found on the news page on the access date.

## 1. Anonymization and double-blind policy

What must be anonymized:

- https://jmlr.org/tmlr/author-guide.html
  > "TMLR uses a double blind review process and submissions must be anonymized."
- https://jmlr.org/tmlr/author-guide.html (supplementary material)
  > "Like submissions, supplementary material must be anonymized."
- https://jmlr.org/tmlr/ae-guide.html (desk rejection)
  > "Clear cases of desk rejection include submissions that are not anonymized, submissions that do not use the unmodified TMLR stylefile and submissions that clearly overlap with work already published in proceedings (or currently under review for publication)."
- https://github.com/JmlrOrg/tmlr-style-file/blob/main/main.tex (template comment)
  > "Authors must not appear in the submitted version. They should be hidden as long as the tmlr package is used without the [accepted] or [preprint] options. Non-anonymous submissions will be rejected without review."
- Same template, on acknowledgments and author contributions:
  > "Only add this information once your submission is accepted and deanonymized."
- The style file prints "Anonymous authors / Paper under double-blind review" in place of the author block in the default mode (`tmlr.sty`, line 132: `\@startauthor Anonymous authors\\Paper under double-blind review \@endauthor`).

arXiv and other public versions:

- https://jmlr.org/tmlr/author-guide.html (Copyright and Licensing)
  > "Authors are also allowed to upload their submissions to arXiv or other preprint servers at any time, either anonymously or including their identity, though double blind of the TMLR submission itself must be maintained by not linking to another version that includes the authors' names."
- https://jmlr.org/tmlr/faq.html
  > "You can still submit, even if a preprint of your work already is available online somewhere (as long as it's not in official proceedings for some other publishing venue). We follow the same approach as double blind conferences, asking that reviewers don't actively search online to figure out who the authors are."
- https://jmlr.org/tmlr/editorial-policies.html
  > "Reviewers are expected not to take any actions that would violate this double blind state, e.g. searching for related presentations or arXiv preprints."
- https://jmlr.org/tmlr/faq.html (who sees the names)
  > "On papers that are submitted but not yet accepted for publication, the author names are hidden Only the action editor assigned to that paper and the editors-in-chief can see the author's."

Public code repositories, anonymized repository links, preregistrations: no TMLR page found that mentions them explicitly. The only applicable rules are the general anonymization requirement and the "not linking to another version that includes the authors' names" sentence above. See "Unverified or not found".

## 2. Length

- https://jmlr.org/tmlr/author-guide.html
  > "Submissions may be any length, but a paper’s length should be justified by its content and papers that are unusually long (not counting any Appendices) are likely to result in reviewing delays."
  > "The submission PDF may include an Appendix, after the references (for proofs, derivations or complimentary results). Looking at the Appendix is at the discretion of the reviewers."
- OpenReview submission form, field "Submission Type" (`submission_length`), read from https://api2.openreview.net/invitations?id=TMLR/-/Submission (invitation last modified 2026-10; form shown on https://openreview.net/group?id=TMLR):
  > "Check if this is a regular length submission, i.e. the main content (all pages before references and appendices) is 12 pages or less. Note that the review process may take significantly longer for papers longer than 12 pages."
  Options: "Regular submission (no more than 12 pages of main content)", "Long submission (more than 12 pages of main content)", "Beyond PDF submission (pageless, webpage-style content)".
- https://jmlr.org/tmlr/reviewer-guide.html (what the threshold changes)
  > "reviews must be submitted within 2 weeks of their assignment by the AE for submissions up to 12 pages (of main content, before references), and 4 weeks for submissions over 12 pages."
- https://jmlr.org/tmlr/faq.html
  > "TMLR does not make any guarantees, and manuscripts whose main body exceeds 12 pages are subject to longer timescales, but in general the rolling review process aims to deliver a final decision approximately 9 weeks after submission."
- https://jmlr.org/tmlr/ae-guide.html
  > "By default, reviewers are asked to submit their review within 2 weeks of their assignment. However, if the submission is longer than 12 pages (excluding any appendix), we ask you to permit a longer reviewing time frame."
- https://jmlr.org/tmlr/faq.html (appendix placement)
  > "Appendices can be included in the main pdf. The supplementary zip file should contain additional material such as videos or code."
- https://jmlr.org/tmlr/faq.html (shorter manuscripts preferred in spirit)
  > "Consider submitting shorter manuscripts to TMLR, and submitting extended works which incorporate previously published material to JMLR."

## 3. Required LaTeX style file

- Repository: https://github.com/JmlrOrg/tmlr-style-file (files `tmlr.sty`, `tmlr.bst`, `fancyhdr.sty`, `main.tex`, `main.bib`, `math_commands.tex`, sample `main.pdf` and `main-accepted.pdf`; last commit 2023-06-30, "Removed duplicated line in tmlr.sty"). The author guide links the ZIP https://github.com/JmlrOrg/tmlr-style-file/archive/refs/heads/main.zip.
- https://jmlr.org/tmlr/author-guide.html
  > "Submissions must be PDF files generated using the TMLR LaTeX stylefile and template."
- https://jmlr.org/tmlr/submissions.html
  > "The Author Guidelines page contains a LaTeX stylefile and template; these are mandatory. Any changes to the stylefile or template that alters the formatting, font, or layout of the manuscript may result in rejection without review."
- Options, from `main.tex` in the repository:
  > "\usepackage{tmlr}
  > % If accepted, instead use the following line for the camera-ready submission:
  > %\usepackage[accepted]{tmlr}
  > % To de-anonymize and remove mentions to TMLR (for example for posting to preprint servers), instead use the following:
  > %\usepackage[preprint]{tmlr}"
  > "You also need to specify the month and year by defining variables {\tt month} and {\tt year}, which respectively should be a 2-digit and 4-digit number."
  Camera-ready also needs `\def\openreview{\url{https://openreview.net/forum?id=XXXX}}` ("Insert correct link to OpenReview for camera-ready version"); the accepted header reads "Published in Transactions on Machine Learning Research (\month/\year)" and the title block adds "Reviewed on OpenReview:".
- https://jmlr.org/tmlr/faq.html (arXiv with the template)
  > "We don't have a policy proscribing the use of our template on arXiv. However, make sure to use the "preprint" option of the stylefile if you do."
- Formatting rules stated in the template (`main.tex`):
  > "The text must be confined within a rectangle 6.5~inches wide and 9~inches long. The left margin is 1~inch. Use 10~point type with a vertical spacing of 11~points."
  > "Do not change any aspects of the formatting parameters in the style files. In particular, do not modify the width or length of the rectangle the text should fit into, and do not change font sizes (except perhaps in the \textbf{References} section; see below). Please note that pages should be numbered."
  > "Please prepare PostScript or PDF files with paper size ``US Letter'', and not, for example, ``A4''."
  The template text says "Computer Modern Bright is the preferred typeface throughout", while `tmlr.sty` itself loads `\usepackage[T1]{fontenc}` and `\usepackage{lmodern}`; using the unmodified `tmlr.sty` settles this.
- Citations and references (`main.tex` and `tmlr.sty`):
  > "Citations within the text should be based on the \texttt{natbib} package and include the authors' last names and year (with the ``et~al.'' construct for more than two authors)."
  > "The corresponding references are to be listed in alphabetical order of authors, in the \textbf{References} section. As to the format of the references themselves, any style is acceptable as long as it is used consistently."
  `tmlr.sty` does `\RequirePackage{natbib}` and `\setcitestyle{authoryear,round,citesep={;},aysep={,},yysep={;}}`; the template ends with `\bibliographystyle{tmlr}`.
- Stylefile requirement does not apply to the separate "Beyond PDF" (HTML) format (https://jmlr.org/tmlr/ae-guide.html): "Note that this stylefile requirement only applies to standard PDF submissions, *not* Beyond PDF submissions."

## 4. LLM / AI-use policy for authors

- https://jmlr.org/tmlr/editorial-policies.html ("LLM use policy for authors")
  > "LLMs may be used as general-purpose assistive tools. Whichever tools are used, authors are fully responsible for content on which they are listed as (co-) authors. This includes, but is not limited to, content generated by LLMs that could be construed as plagiarism or scientific misconduct (e.g., fabrication of facts). Low-quality contributions (be they submissions or reviews) that appear to be largely LLM-generated will be closely examined for evidence of the issues mentioned previously, such as scientific misconduct. LLMs are not eligible for authorship. We will periodically revise this policy as new information about the use of LLMs in the scientific process becomes available."
- https://jmlr.org/tmlr/faq.html ("Can I use ChatGPT or other large language model systems to assist in writing my TMLR submission?")
  > "Yes, but TMLR also considers that it is the authors' responsibility to avoid any unforeseen consequences that might come about from using such tools, such as the later discovery that a significant part of the submission's content has been plagiarized (in which case we'd have to reject the paper). Similarly, our expectation is that the ideas, claims and results found in submissions are human-sourced, not produced by such tools."
  > "Additionally, transparency is always good, so we also require that authors mention explicitly in their submission that they have used this tool, as a footnote on the first page."
- https://jmlr.org/tmlr/acceptance-criteria.html
  > "If a paper fully is AI generated with little or no human involvement, then at least with current AI systems, it is unlikely to meet this criterion."
- Note: the first-page-footnote requirement appears only in the FAQ, not in the editorial policy; complying with both (footnote plus the existing statement section) is the safe reading.

## 5. Supplementary material and code

- https://jmlr.org/tmlr/author-guide.html
  > "Authors may submit up to 100MB of supplementary material, such data, source code or illustrative videos; all supplementary materials must be in PDF or ZIP format. Supplementary material should be material created by the authors that directly supports the submission content. Like submissions, supplementary material must be anonymized. Looking at supplementary material is at the discretion of the reviewers."
  > "We encourage authors to, whenever possible, upload materials that improve reproducibility. Specifically, it is suggested that authors submit supplementary material including data or code towards this end."
- OpenReview form, field `supplementary_material` (optional, `zip` or `pdf`, max 100 MB):
  > "All supplementary material must be self-contained and zipped into a single file. Note that supplementary material will be visible to reviewers and the public throughout and after the review period, and ensure all material is anonymized. The maximum file size is 100MB."
- OpenReview form, field `pdf`: "Upload a PDF file that ends with .pdf." (parameter `maxSize: 50`, i.e. 50 MB).
- OpenReview form, field `beyond_pdf`: "Please do not upload LaTeX source code for a standard PDF submission here."
- https://jmlr.org/tmlr/editorial-policies.html (after acceptance)
  > "The author is encouraged to submit additional materials that can help to support their paper, such as a video presentation or code."
- https://jmlr.org/tmlr/faq.html
  > "Code and videos may be uploaded and associated with camera ready papers."
- Code is encouraged, not required.

## 6. OpenReview profile requirements

TMLR side:

- https://jmlr.org/tmlr/author-guide.html
  > "All authors must have complete and active OpenReview profiles, including information such as affiliations, conflicts of interest, and publication history."
- https://jmlr.org/tmlr/editorial-policies.html
  > "The exact set of authors must be listed on OpenReview, with active OpenReview profiles, at the time of submission and throughout the review process. No authors may be added or removed after submission. There are no exceptions to this policy."
  > "Authors and co-authors will use their OpenReview profile to identify domain and personal conflicts. Domain conflicts, entered in Education & Career History, are used to identify institutions with which you have a conflict of interest from (at least) the last three years."
- OpenReview form, field `authorids`: "Search author profile by name or OpenReview profile ID. All authors must have an OpenReview profile."

OpenReview side (no institutional e-mail):

- https://docs.openreview.net/getting-started/creating-an-openreview-profile/signing-up-for-openreview
  > "We recommend that you sign up with your institutional (university, company, or organization) email."
  > "Signing up with a public domain may take up to 2 weeks in moderation."
  Sign-up warning shown for a public domain: "It can take up to 2 weeks for profiles using public email services to be activated."
  > "Providing as complete information as possible, especially an institutional email address and valid personal homepage, will help your account be activated quickly."
  > "A valid homepage is a website that shows your name, affiliation, and email that you used to register for OpenReview. This could be a Google Scholar profile, personal webpage, GitHub, institutional profile page, or other professional homepage."
  > "After clicking ‘Register for OpenReview’, your profile will either be activated immediately or sent to moderation."
- https://docs.openreview.net/getting-started/frequently-asked-questions/i-am-an-independent-researcher-how-do-i-sign-up
  > "If you are not affiliated with an academic institution, but are employed at a company, you can use that domain and position information to sign up. This is recommended if at all possible."
  > "If you do not have a company domain, you can use a personal email. All personal emails will be moderated"
  > "For the Position field select **'Independent Researcher'**, which will lock the Institution Info domains automatically."
  > "Please include as much of your background as possible. If the 'Career & Education History' section only lists 'Independent Researcher' your profile will be rejected with a request to add another institution record."
  > "Please do not use an old role or affiliation as your current position, as that may delay moderation."
- https://docs.openreview.net/getting-started/creating-an-openreview-profile/expediting-profile-activation
  > "If you don’t have any institutional emails, please ensure your other profile information is complete. Ensuring your homepage displays your email and career details, along with a fully completed profile, will facilitate the activation process. We will follow up if we need more information."
  > "After creating an account, you can set your preferred email to your personal email account, and this will be the email used for submissions and notifications."

Reviewing obligation for authors: none found on any TMLR page or in the submission form. Related facts:

- https://jmlr.org/tmlr/editorial-policies.html: "Authors who are reviewers or action editors enjoy doubled quotas (N_1 = 4, N_9 = 18)."
- https://jmlr.org/tmlr/faq.html: reviewer pool is joined voluntarily ("You can volunteer to join the reviewer pool ... by filling out these forms").

## 7. Review process, timeline, decisions, certifications

- https://jmlr.org/tmlr/editorial-policies.html
  > "Submission. The manuscript is submitted to OpenReview in anonymized form, and the authors recommend an action editor to oversee the review process."
  > "Reviewing. An action editor will be assigned to the submission within a week. They will evaluate the submission, and may reject it immediately for reasons including (but not limited to): being out of scope, TMLR having insufficient reviewer expertise to adequately handle, being poor quality or unlikely to meet TMLR's acceptance criteria, or having format violations (contingent on Editor-in-Chief approval). Otherwise, the action editor will assign at least three qualified reviewers and the paper will become public."
  > "Authors can respond to a review as soon as it is posted, however we recommend waiting until all 3 reviews have been submitted before submitting any revised version of the PDF manuscript. Reviewers will be able to submit their final recommendations once at least two weeks have elapsed after all 3 reviews became public."
  > Decisions: "Accept as is", "Accept with minor revision", "Reject" ("the action editor indicates whether they would be willing to consider a significantly revised version of the manuscript").
  > "Authors of a rejected submission may revise and resubmit their paper, but it will need to be entered as a new submission and a link provided to the previously rejected submission as well as a description of the changes made since."
- https://jmlr.org/tmlr/submissions.html
  > "You will receive an email once your submission has been made, asking you to recommend potential Action Editors that would be appropriate for your submission."
- https://jmlr.org/tmlr/ae-guide.html
  > "The first step following an AE assignment is to determine (within 1 week) whether or not the submitted preprint is appropriate for TMLR and respects our submission guidelines."
  > "reviewers will submit their own recommendation to you on a decision for a submission no sooner than 2 weeks and no later than 4 weeks after the submission of the third review."
  > "Once all 3 reviewer decision recommendations have been submitted, you should aim to submit your decision proposal within 1 week. Your decision proposal should therefore be submitted within 5 weeks of the beginning of the discussion between authors and reviewers."
- https://jmlr.org/tmlr/faq.html
  > "The discussion phase will be at least 2 weeks and up to 4 weeks long."
  > "We strongly recommend that authors submit responses, including any revisions, no later than 2 weeks after the submission of the 3rd review."
  > "Generally, authors should not expect an extension to be granted."
  > "All submitted papers, including those accepted, rejected, withdrawn, or retracted, are made publicly accessible on OpenReview. An exception is made for desk-rejected papers, which are never made public."
- Acceptance criteria (https://jmlr.org/tmlr/editorial-policies.html):
  > "Are the claims made in the submission supported by accurate, convincing and clear evidence?" / "Would at least some individuals in TMLR's audience be interested in knowing the findings of this paper?"
  > "Papers should be accepted if they meet the criteria, even if the contribution or significance of the work is modest."
  https://jmlr.org/tmlr/acceptance-criteria.html adds: "Another is for the authors to adjust (reduce) their claims." and "novelty of the studied method is not a necessary criterion for acceptance in TMLR."
- Certifications (https://jmlr.org/tmlr/editorial-policies.html): "Accepted papers will be automatically considered for a number of certifications". Listed: Outstanding, Featured, Reproducibility, Survey, J2C ("Awarded to publications based on responses by the AE and reviewers, to the question of whether the work would be appropriate for the joint NeurIPS/ICLR/ICML Journal-to-Conference Track"), Expert ("Awarded to papers that are authored by highly-rated TMLR reviewers"). Note https://jmlr.org/tmlr/faq.html: "As of September 1, 2026, TMLR no longer considers survey papers for review."
- Holiday pause (https://jmlr.org/tmlr/news/): "2025.11.15: TMLR will pause new submissions over the upcoming holiday period from December 2 2025 to January 5 2026 (midnight AOE on both dates)." A similar pause ran from 2 December 2024 to 6 January 2025. No 2026 announcement was listed on the access date.

## 8. Prior and concurrent publication

- https://jmlr.org/tmlr/editorial-policies.html ("Dual Submissions and Originality")
  > "Unlike many other journals, TMLR only accepts original contributions that don’t reuse the authors’ own prior work. In particular, we do not accept submissions that are expanded versions of conference papers. There should not be any reuse of written text, figures or results between the submitted paper and any paper which has been published, accepted for publication, or submitted in parallel at another archival, peer-reviewed venue. It is acceptable for a submission to overlap with the author's previous work if it was shared at venues or tracks that are publicly declared, in writing, to be non-archival, such as workshops, or on preprint servers such as arXiv and bioRxiv."
- https://jmlr.org/tmlr/author-guide.html: arXiv upload allowed "at any time, either anonymously or including their identity" (full quote in section 1).
- https://jmlr.org/tmlr/faq.html: preprints allowed "as long as it's not in official proceedings for some other publishing venue"; thesis work "is considered similarly to a pre-print, e.g., on arXiv."

## 9. Other items for a first-time submitter

- Submission form fields (https://api2.openreview.net/invitations?id=TMLR/-/Submission): title (max 250 characters), abstract (max 5000 characters, TeX allowed), authors and author profile IDs, PDF, Submission Type (Regular / Long / Beyond PDF), optional supplementary material, optional previous TMLR submission URL and "changes since last submission", and two mandatory text fields:
  - `competing_interests`: "Beyond those reflected in the authors' OpenReview profile, disclose relationships (notably financial) of any author with entities that could potentially be perceived to influence what you wrote in the submitted work, during the last 36 months prior to this submission. This would include engagements with commercial companies or startups (sabbaticals, employments, stipends), honorariums, donations of hardware or cloud computing services. Enter "N/A" if this question isn't applicable to your situation."
  - `human_subjects_reporting`: "If the submission reports experiments involving human subjects, provide information available on the approval of these experiments, such as from an Institutional Review Board (IRB). Enter "N/A" if this question isn't applicable to your situation."
  - After submission, an e-mail asks for recommended action editors (https://jmlr.org/tmlr/submissions.html); the editorial board list is https://jmlr.org/tmlr/editorial-board.html.
- Broader impact (https://jmlr.org/tmlr/author-guide.html):
  > "If their work carries a significant risk of harm, authors are required to include a Statement of Broader Impact."
  The template calls it an "optional section" and places `\subsubsection*{Broader Impact Statement}` before Author Contributions and Acknowledgments.
- Licence and copyright (https://jmlr.org/tmlr/author-guide.html):
  > "All TMLR submissions, from the time of submission to final publication, are licensed under CC BY 4.0. At all times, copyright is retained by the authors."
- Fees (https://jmlr.org/tmlr/editorial-policies.html): "TMLR imposes no fees or payments to authors, reviewers, action editors, or editors-in-chief."
- Quota (https://jmlr.org/tmlr/editorial-policies.html): "Authors are restricted in the number of submissions they can make per year, according to the Generalized Harmonic Quota Rule, with parameters N_1 = 2 and N_9 = 9." "Budget is spent for all submissions by an author, including those which are desk rejected." (Checker: https://www.cs.cmu.edu/~nihars/quota/author.html?rule=generalized&N1=2&A=9&NA=9.)
- Authorship criteria and testimony (https://jmlr.org/tmlr/editorial-policies.html, "Criteria for Authorship"); "Authors may choose to include a statement indicating author contributions."
- Withdrawal (https://jmlr.org/tmlr/editorial-policies.html): "the submission will remain on OpenReview but its status will be explicitly marked as withdrawn."
- Camera-ready (https://jmlr.org/tmlr/ae-guide.html): the AE verifies that "the camera ready manuscript complies with TMLR stylefile, with all author information inserted in the manuscript as well as the link to the OpenReview page for the submission." Minor revisions go into the camera-ready (https://jmlr.org/tmlr/faq.html: "The required revisions should be made in the camera ready submission."). Post-publication changes go in a section titled "Post-Publication Changes" (https://jmlr.org/tmlr/editorial-policies.html).
- Required reading before submitting (https://jmlr.org/tmlr/author-guide.html): "Authors are required to also read and be familiar with the Editorial Policies, the Acceptance Criteria, the Ethics Guidelines, and the Code of Conduct".

## Implications for this paper

Checked against the repository state of 2026-11-17 (`paper/main.tex`, `paper/preamble.tex`, `paper/sections/*.tex`, `paper/build/main.pdf`).

1. Anonymized build (required; missing it is a clear desk-rejection case).
   - Replace `\documentclass[11pt]{article}` + `\input{preamble.tex}` layout with `\documentclass[10pt]{article}` and `\usepackage{tmlr}` (no option) for the submission; the author block (name, "Independent researcher", ORCID) is then hidden by the style file.
   - Remove or withhold every identifying link in the anonymized build: `https://github.com/zoli84-cmd/ncm-sudoku-research` (the user name identifies the author) and the OSF links `https://osf.io/hb8vq`, `https://osf.io/m28fx`, DOI `10.17605/OSF.IO/HB8VQ` (the public registration shows the author's name) in `sections/appendix.tex` line 20 and `sections/setup.tex` line 28. TMLR's only explicit rule is "not linking to another version that includes the authors' names"; the safe reading treats the named repository and the named registration the same way. Options: "[link withheld for double-blind review]", and/or an anonymized ZIP of the code and the frozen registration text as supplementary material (no `.git` history, no author name in README, LICENSE, `pyproject.toml` or file metadata).
   - Do not cite or link the arXiv version of this paper in the submission. The arXiv version itself may stay public.
   - Keep acknowledgments and any author-contribution statement out until acceptance.
   - Check the PDF metadata (title/author fields set by hyperref) for the author name.
2. Length. The current build has its main text on pages 1 to 18 (references start on page 19), with 11 pt type and 1.1 inch margins. TMLR uses 10 pt type on a 6.5 x 9 inch text block, so the page count will drop, but the result is not known until the paper is rebuilt with `tmlr.sty`. Unless the main text fits in 12 pages after the rebuild, the paper must be submitted as "Long submission (more than 12 pages of main content)", with 4-week reviews and a timeline longer than the roughly 9 weeks given for regular submissions. Moving material to the appendix (which does not count) is the lever if a regular submission is wanted.
3. Style file. Vendor the unmodified `tmlr.sty`, `tmlr.bst`, `fancyhdr.sty` (and optionally `math_commands.tex`) from https://github.com/JmlrOrg/tmlr-style-file into `paper/`. Remove from the TMLR build anything that changes layout or fonts: `\usepackage[letterpaper,margin=1.1in]{geometry}` (alters the text block) and `\usepackage[numbers]{natbib}` (tmlr.sty already loads natbib with author-year; the `numbers` option would also clash). Switch `\bibliographystyle{plainnat}` to `\bibliographystyle{tmlr}`; `\citep`/`\citet` usage then renders author-year. Keep `\appendix` after the bibliography (already so). Pages must be numbered; paper size US Letter (already letterpaper). Check that the `\footnotesize` tables in `sections/summary.tex` and `sections/appendix.tex` still fit the 6.5 inch width. A separate non-anonymous build with `[preprint]` is optional; the FAQ asks for the `preprint` option only if the TMLR template is used on arXiv.
4. AI statement. The existing "Use of AI tools" section (`sections/statements.tex`) is consistent with the editorial policy (assistive use, full author responsibility, no AI authorship). The FAQ additionally requires LLM use to be mentioned "as a footnote on the first page"; add a short first-page footnote (for example on the title or the first page of the introduction) that points to the statement. Its wording "The author" is not identifying by itself, but it reveals single authorship; this is a judgment call, not a stated TMLR rule.
5. OpenReview profile timing. Without an institutional e-mail, moderation "may take up to 2 weeks", and a profile listing only "Independent Researcher" is rejected; add earlier institution records (education and past positions with dates) and a homepage that shows name, affiliation and the registration e-mail (for example the GitHub profile or ORCID page, if it shows these). If the author has a company e-mail domain, OpenReview recommends using it. Create the profile now; the profile must be active before submission. If TMLR repeats its holiday pause from 2 December (2024 and 2025 pattern; 2026 not announced on the access date), a profile created on 2026-11-17 could still be in moderation when submissions pause, which would push the submission into January 2027.
6. Form fields to prepare: abstract (current abstract is well under 5000 characters but uses `\R{}` macros, so paste the rendered text), competing interests (likely "N/A" unless an employment relationship needs disclosure), human subjects ("N/A"), Submission Type (see item 2), optional anonymized supplementary ZIP (max 100 MB), PDF max 50 MB, a list of suggested action editors from https://jmlr.org/tmlr/editorial-board.html. Check the quota tool for a single-author submission.
7. Licence. CC BY 4.0 applies from submission; this matches the paper's existing CC BY 4.0 statement in `sections/appendix.tex`. No change needed.
8. Broader impact. Not required unless the work "carries a significant risk of harm"; an interpretability study of a Sudoku generator plausibly does not, so the section is optional.
9. Prior publication. The arXiv preprint (submitted 2026-11-17) and the public OSF preregistration are not archival peer-reviewed publications; nothing in the TMLR rules prevents submission on that account.

## Unverified or not found

- Anonymized repository links (for example anonymous.4open.science): no TMLR page mentions them, neither allowing nor forbidding them. The recommendation above follows from the general anonymization rule only.
- Preregistrations (OSF): no TMLR page mentions preregistrations or how to cite a public, named registration during double-blind review. Whether OSF anonymized view-only links are acceptable is not addressed by TMLR; OSF documentation was not consulted (out of the requested source scope).
- Public code repositories under the author's name: not addressed explicitly; covered only by "not linking to another version that includes the authors' names" and the general anonymization requirement.
- Reviewing requirement for authors: none found on jmlr.org/tmlr pages, in the OpenReview submission form, or in the TMLR OpenReview group description. Only the doubled quota for reviewers was found.
- Holiday pause for 2026/2027: not announced on https://jmlr.org/tmlr/news/ on the access date; the December pause is a two-year pattern only.
- Typeface: the template text says "Computer Modern Bright is the preferred typeface", while `tmlr.sty` loads `lmodern`; no primary source resolves this beyond "do not modify the style file".
- Exact OpenReview moderation time: OpenReview gives "up to 2 weeks" for public-domain e-mails; no other primary figure exists.
- The 50 MB PDF limit is read from the form's `maxSize: 50` parameter (OpenReview API), not from a sentence on a TMLR page.
- Pages fetched without error: jmlr.org/tmlr author-guide, editorial-policies, submissions, faq, reviewer-guide, ae-guide, acceptance-criteria, ethics, code, index, news; the TMLR style-file repository (README, main.tex, tmlr.sty, file list, commit log via the GitHub API); the OpenReview API invitation `TMLR/-/Submission` and group `TMLR`; the three OpenReview documentation pages cited. No page failed to load.
