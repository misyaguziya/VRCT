import styles from "./AboutVrct.module.scss";
import dev_section_title from "@images/about_vrct/dev_section_title.png";
import dev_misya from "@images/about_vrct/dev_misya.png";
import dev_shiina from "@images/about_vrct/dev_shiina.png";
import vrct_logo_for_about_vrct from "@images/about_vrct/vrct_logo_for_about_vrct.png";
import contributors_section_title from "@images/about_vrct/contributors_section_title.png";
import contributors_members from "@images/about_vrct/contributors_members.png";
import localization_section_title from "@images/about_vrct/localization_section_title.png";
import localization_members from "@images/about_vrct/localization_members.png";

import special_thanks_section_title from "@images/about_vrct/special_thanks_section_title.png";
import special_thanks_members from "@images/about_vrct/special_thanks_members.png";
import special_thanks_message_en from "@images/about_vrct/special_thanks_message_en.png";
import special_thanks_message_ja from "@images/about_vrct/special_thanks_message_ja.png";

import poster_showcase_section_title from "@images/about_vrct/poster_showcase_section_title.png";

import vrchat_disclaimer from "@images/about_vrct/vrchat_disclaimer.png";

import clsx from "clsx";
import { useTranslation } from "react-i18next";
import { useUiLanguage } from "@store";
import { PosterShowcaseContents } from "./poster_showcase_contents/PosterShowcaseContents";

export const AboutVrct = () => {
    const { t } = useTranslation();
    const { currentUiLanguage } = useUiLanguage();
    return (
        <div className={styles.container}>
            <div className={styles.dev_section}>
                <img src={dev_section_title} className={clsx(styles.section_title, styles.the_developers)} />
                <div className={styles.dev_section_wrapper}>
                    <div className={styles.dev_card_wrapper}>
                        <img src={dev_misya} className={styles.dev_card_img} />
                        <OpenLinkContainer className={styles.dev_misya_x} href_id="dev_misya_x" />
                        <OpenLinkContainer className={styles.dev_misya_github} href_id="dev_misya_github" />
                    </div>
                    <div className={styles.dev_card_wrapper}>
                        <img src={dev_shiina} className={styles.dev_card_img} />
                        <OpenLinkContainer className={styles.dev_shiina_x} href_id="dev_shiina_x" />
                    </div>
                </div>
            </div>

            <div className={styles.project_links_and_logo_section}>
                <img src={vrct_logo_for_about_vrct} className={styles.about_vrct_logo} />
                <div className={styles.project_links_wrapper}>
                    <OpenLinkContainer className={styles.project_link} href_id="project_link_booth" />
                    <OpenLinkContainer className={styles.project_link} href_id="project_link_documents" />
                    <OpenLinkContainer className={styles.project_link} href_id="project_link_vrct_github" />
                    <OpenLinkContainer className={styles.project_link} href_id="project_link_contact_us" />
                </div>
            </div>

            <div className={styles.contributors_section}>
                <img src={contributors_section_title} className={clsx(styles.section_title, styles.contributors)} />
                <div className={styles.contributors_img_wrapper}>
                    <img src={contributors_members} className={clsx(styles.contributors_img, styles.contributors)} />
                    <OpenLinkContainer className={styles.contributors_done_san_x} href_id="contributors_done_san_x" />
                    <OpenLinkContainer className={styles.contributors_iya_x} href_id="contributors_iya_x" />
                    <OpenLinkContainer className={styles.contributors_rera_x} href_id="contributors_rera_x" />
                    <OpenLinkContainer className={styles.contributors_rera_github} href_id="contributors_rera_github" />
                    <OpenLinkContainer className={styles.contributors_poposuke_x} href_id="contributors_poposuke_x" />
                    <OpenLinkContainer className={styles.contributors_kumaguma_x} href_id="contributors_kumaguma_x" />
                </div>
            </div>

            <div className={styles.localization_section}>
                <img src={localization_section_title} className={clsx(styles.section_title, styles.localization)} />
                <img src={localization_members} className={clsx(styles.localization_members_img, styles.localization)} />
            </div>

            <div className={styles.special_thanks_section}>
                <img src={special_thanks_section_title} className={clsx(styles.section_title, styles.special_thanks)} />
                <img src={special_thanks_members} className={styles.special_thanks_members_img} />
                {
                    currentUiLanguage === "ja"
                    ? <img src={special_thanks_message_ja} className={styles.special_thanks_message_img} />
                    : <img src={special_thanks_message_en} className={styles.special_thanks_message_img} />
                }
            </div>


            <div className={styles.poster_showcase_section}>
                <img src={poster_showcase_section_title} className={clsx(styles.section_title, styles.poster_showcase)} />
                <PosterShowcaseContents />
            </div>

            <div className={styles.vrchat_disclaimer_section}>
                <img src={vrchat_disclaimer} className={styles.vrchat_disclaimer} />
            </div>


        </div>
    );
};

import dev_x_icon from "@images/about_vrct/dev_x_icon.png";
import dev_github_icon from "@images/about_vrct/dev_github_icon.png";
import contributors_x_icon from "@images/about_vrct/contributors_x_icon.png";
import contributors_github_icon from "@images/about_vrct/contributors_github_icon.png";

import project_link_booth from "@images/about_vrct/project_link_booth.png";
import project_link_documents from "@images/about_vrct/project_link_documents.png";
import project_link_vrct_github from "@images/about_vrct/project_link_vrct_github.png";
import project_link_contact_us from "@images/about_vrct/project_link_contact_us.png";

const about_vrct_links = {
    dev_misya_x: { img: dev_x_icon, href: "https://twitter.com/misya_ai" },
    dev_misya_github: { img: dev_github_icon, href: "https://github.com/misyaguziya" },
    dev_shiina_x: { img: dev_x_icon, href: "https://twitter.com/Shiina_12siy" },

    project_link_booth: { img: project_link_booth, href: "https://misyaguziya.booth.pm/items/5155325" },
    project_link_documents: { img: project_link_documents, href: "https://mzsoftware.notion.site/VRCT-Documents-be79b7a165f64442ad8f326d86c22246" },
    project_link_vrct_github: { img: project_link_vrct_github, href: "https://github.com/misyaguziya/VRCT" },
    project_link_contact_us: { img: project_link_contact_us, href: "https://docs.google.com/forms/d/e/1FAIpQLSei-xoydOY60ivXqhOjaTzNN8PiBQIDcNhzfy6cw2sjYkcg_g/viewform" },

    contributors_done_san_x: { img: contributors_x_icon, href: "https://twitter.com/done_vrc" },
    contributors_iya_x: { img: contributors_x_icon, href: "https://twitter.com/IYAA_HHHH" },
    contributors_rera_x: { img: contributors_x_icon, href: "https://twitter.com/rerassi" },
    contributors_rera_github: { img: contributors_github_icon, href: "https://github.com/soumt-r" },
    contributors_poposuke_x: { img: contributors_x_icon, href: "https://twitter.com/sig_popo" },
    contributors_kumaguma_x: { img: contributors_x_icon, href: "https://twitter.com/K_kumaguma_A" },
};

const OpenLinkContainer = ({className, href_id}) => {
    const href = about_vrct_links[href_id].href;
    const img = about_vrct_links[href_id].img;
    return (
        <a className={className} href={href} target="_blank" rel="noreferrer" >
            {/* for adjust size to their parent component's width. */}
            <img style={ {height: "100%", width: "100%", "objectFit": "contain" }} src={img} />
        </a>
    );
};