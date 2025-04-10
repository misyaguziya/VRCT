import styles from "./ContactsContainer.module.scss";

export const ContactsContainer = () => {
    return (
        <div className={styles.container}>
            <OpenLinkContainer className={styles.github_issues} href_id="github_issues" text="Github Issues"/>
            <OpenLinkContainer className={styles.google_forms} href_id="google_forms" text="Google Forms"/>
        </div>
    );
};

import dev_github_icon from "@images/about_vrct/dev_github_icon.png";
import document from "@images/document.png";

const contacts_links = {
    github_issues: { img: dev_github_icon, href: "https://github.com/misyaguziya/VRCT/issues" },
    google_forms: { img: document, href: "https://docs.google.com/forms/d/e/1FAIpQLSei-xoydOY60ivXqhOjaTzNN8PiBQIDcNhzfy6cw2sjYkcg_g/viewform" },
};

const OpenLinkContainer = ({className, href_id, text}) => {
    const href = contacts_links[href_id].href;
    const img = contacts_links[href_id].img;
    return (
        <a className={className} href={href} target="_blank" rel="noreferrer" >
            <img className={styles.contact_button_icon} src={img} />
            <p className={styles.contact_button_label}>{text}</p>
        </a>
    );
};