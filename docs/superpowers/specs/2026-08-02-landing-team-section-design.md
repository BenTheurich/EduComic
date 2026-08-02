# Landing Team Section Design

## Job and audience

The section closes the public landing page by showing the five people who made EduComic. It should make the project feel personal and credible without becoming a corporate biography grid or distracting from the product story above it.

## Selected direction

Use a full-width workshop-blue section immediately after the four-step scrolling sequence. Treat it like the back-cover credits of the comic: one centered heading, five illustrated portraits, and a restrained technology credit.

The heading is **Meet the team behind EduComic.** The five teammates appear with equal visual weight in this order:

1. Florian Schwieren
2. Pouya Shekarchizadeh
3. Anastasia Koslova
4. Tim Gaydoul
5. Ben Theurich

This order alternates the portraits' visual characteristics and places Anastasia at the center of the five-person desktop row. No person is labelled as the lead.

## Portrait treatment

- Generate one school-age illustrated avatar from each supplied adult photo, imagining each teammate at approximately 10 to 12 years old.
- Generate each portrait independently, using the same prompt, shoulder-up crop, expression, lighting, line treatment, pale blue background, and existing student-avatar style reference.
- Preserve recognizable features from each teammate while matching the friendly cartoon proportions and finish of the student avatar bubbles.
- Present every avatar in an equal circular frame with a white rim and restrained shadow.
- Do not add cards, biographies, roles, badges, or decorative props.
- Do not place the original photographs in the public application assets.
- Use concise alternative text in the form `Illustrated portrait of [name]`.

## Names and links

Each portrait is followed by the teammate's full name and a visible `LinkedIn` text link. The links are:

- Florian Schwieren: https://www.linkedin.com/in/florian-schwieren-618750215/
- Pouya Shekarchizadeh: https://www.linkedin.com/in/pooyash1998/
- Anastasia Koslova: https://www.linkedin.com/in/anastasia-koslova-a329091b7/
- Tim Gaydoul: https://www.linkedin.com/in/tim-gaydoul-048788174/
- Ben Theurich: https://www.linkedin.com/in/ben-theurich/

External links open in a new tab, use `rel="noreferrer"`, and retain a visible keyboard focus state. The full name remains visible text rather than being replaced by an icon.

## Technology credit

The provider attribution is a compact line inside the team section, separated from the portraits by a thin translucent rule. It is not a second feature section and it uses no provider logos.

Copy: **Built with FLUX by Black Forest Labs for artwork and OpenAI for story generation.**

`Black Forest Labs` and `OpenAI` are descriptive text links to their official sites. The treatment must not imply sponsorship, partnership, or endorsement.

## Layout and motion

- Desktop: one centered row of five portraits.
- Tablet: a centered three-plus-two wrap.
- Mobile: a centered two-plus-two-plus-one grid with comfortable portrait sizes.
- Keep the section generous enough to feel like a closing chapter, but shorter than a full scrolling process step.
- Reveal the five portraits together with one subtle fade and upward movement when the section enters view. Do not stagger them.
- Disable the entrance transform when reduced motion is requested.

## Scope and boundaries

- Append the team section after the existing scrolling section.
- Preserve the hero, process sequence, copy, sticky behavior, colors, and existing generated product imagery.
- Reuse the current landing-page typography, workshop blue, paper white, borders, and motion conventions.
- Add no dependency and no content-management abstraction. The five entries are static landing-page content.

## Verification

- Extend the landing-page component test to verify the heading, five names, five LinkedIn destinations, and technology credit.
- Run the existing frontend test suite and production build.
- Inspect the finished page once at representative desktop and mobile widths, including keyboard focus and reduced motion.
