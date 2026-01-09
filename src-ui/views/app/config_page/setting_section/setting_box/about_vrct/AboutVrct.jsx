import styles from "./AboutVrct.module.scss";
import dev_section_title from "@images/about_vrct/dev_section_title.png";
import dev_misya from "@images/about_vrct/dev_misya.png";
import dev_shiina from "@images/about_vrct/dev_shiina.png";
import vrct_logo_for_about_vrct from "@images/about_vrct/vrct_logo_for_about_vrct.png";

import contributors_section_title from "@images/about_vrct/contributors_section_title.png";
import contributor_done from "@images/about_vrct/contributor_done.png";
import contributor_iya from "@images/about_vrct/contributor_iya.png";
import contributor_rera from "@images/about_vrct/contributor_rera.png";
import contributor_poposuke from "@images/about_vrct/contributor_poposuke.png";
import contributor_kumaguma from "@images/about_vrct/contributor_kumaguma.png";
import contributor_riku from "@images/about_vrct/contributor_riku.png";

import localization_section_title from "@images/about_vrct/localization_section_title.png";
import localization_1 from "@images/about_vrct/localization_1.png";
import localization_2 from "@images/about_vrct/localization_2.png";
import localization_3 from "@images/about_vrct/localization_3.png";
import localization_4 from "@images/about_vrct/localization_4.png";
import localization_5 from "@images/about_vrct/localization_5.png";

import special_thanks_section_title from "@images/about_vrct/special_thanks_section_title.png";
import special_thanks_members from "@images/about_vrct/special_thanks_members.png";
import special_thanks_message_en from "@images/about_vrct/special_thanks_message_en.png";
import special_thanks_message_ja from "@images/about_vrct/special_thanks_message_ja.png";

import poster_showcase_section_title from "@images/about_vrct/poster_showcase_section_title.png";

import clsx from "clsx";
import { useI18n } from "@useI18n";
import { useAppearance } from "@logics_configs";
import { PosterShowcaseContents } from "./poster_showcase_contents/PosterShowcaseContents";

import { generateLocalizedDocumentUrl } from "@ui_configs";

export const AboutVrct = () => {
    const { t } = useI18n();
    const { currentUiLanguage } = useAppearance();
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
                <div className={styles.about_vrct_logo_wrapper}>
                    <img src={vrct_logo_for_about_vrct} className={styles.about_vrct_logo} />
                </div>
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
                    <div className={styles.contributor_card_wrapper}>
                        <img src={contributor_done} className={clsx(styles.contributors_img, styles.contributors)} />
                        <OpenLinkContainer className={styles.contributors_done_san_x} href_id="contributors_done_san_x" />
                    </div>
                    <div className={styles.contributor_card_wrapper}>
                        <img src={contributor_iya} className={clsx(styles.contributors_img, styles.contributors)} />
                        <OpenLinkContainer className={styles.contributors_iya_x} href_id="contributors_iya_x" />
                    </div>
                    <div className={styles.contributor_card_wrapper}>
                        <img src={contributor_rera} className={clsx(styles.contributors_img, styles.contributors)} />
                        <OpenLinkContainer className={styles.contributors_rera_x} href_id="contributors_rera_x" />
                        <OpenLinkContainer className={styles.contributors_rera_github} href_id="contributors_rera_github" />
                    </div>
                    <div className={styles.contributor_card_wrapper}>
                        <img src={contributor_poposuke} className={clsx(styles.contributors_img, styles.contributors)} />
                        <OpenLinkContainer className={styles.contributors_poposuke_x} href_id="contributors_poposuke_x" />
                    </div>
                    <div className={styles.contributor_card_wrapper}>
                        <img src={contributor_kumaguma} className={clsx(styles.contributors_img, styles.contributors)} />
                        <OpenLinkContainer className={styles.contributors_kumaguma_x} href_id="contributors_kumaguma_x" />
                    </div>
                    <div className={styles.contributor_card_wrapper}>
                        <img src={contributor_riku} className={clsx(styles.contributors_img, styles.contributors)} />
                        <OpenLinkContainer className={styles.contributors_riku_x} href_id="contributors_riku_x" />
                    </div>
                </div>
            </div>

            <div className={styles.localization_section}>
                <img src={localization_section_title} className={clsx(styles.section_title, styles.localization)} />
                <div className={styles.localization_members_wrapper}>
                    <div className={styles.localization_members_row_wrapper}>
                        <img src={localization_1} className={styles.localization_members_img} />
                        <img src={localization_2} className={styles.localization_members_img} />
                    </div>
                    <div className={styles.localization_members_row_wrapper}>
                        <img src={localization_3} className={styles.localization_members_img} />
                        <img src={localization_4} className={styles.localization_members_img} />
                    </div>
                    <div className={styles.localization_members_row_wrapper}>
                        <img src={localization_5} className={styles.localization_members_img} />
                        {/* <img src={localization_6} className={styles.localization_members_img} /> */}
                    </div>
                </div>
            </div>

            <div className={styles.special_thanks_section}>
                <img src={special_thanks_section_title} className={clsx(styles.section_title, styles.special_thanks)} />
                <img src={special_thanks_members} className={styles.special_thanks_members_img} />
                {
                    currentUiLanguage.data === "ja"
                    ? <img src={special_thanks_message_ja} className={styles.special_thanks_message_img} />
                    : <img src={special_thanks_message_en} className={styles.special_thanks_message_img} />
                }
            </div>


            <div className={styles.poster_showcase_section}>
                <img src={poster_showcase_section_title} className={clsx(styles.section_title, styles.poster_showcase)} />
                <PosterShowcaseContents />
            </div>

            <div className={styles.vrchat_disclaimer_section}>
                <p className={styles.vrchat_disclaimer}>VRCT is not endorsed by VRChat and does not reflect the views or opinions of VRChat or anyone officially involved in producing or managing VRChat properties. VRChat and all associated properties are trademarks or registered trademarks of VRChat Inc. VRChat © VRChat Inc.</p>
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
    project_link_documents: { img: project_link_documents, href: generateLocalizedDocumentUrl().vrct_document_home_url },
    project_link_vrct_github: { img: project_link_vrct_github, href: "https://github.com/misyaguziya/VRCT" },
    project_link_contact_us: { img: project_link_contact_us, href: "https://docs.google.com/forms/d/e/1FAIpQLSei-xoydOY60ivXqhOjaTzNN8PiBQIDcNhzfy6cw2sjYkcg_g/viewform" },

    contributors_done_san_x: { img: contributors_x_icon, href: "https://twitter.com/done_vrc" },
    contributors_iya_x: { img: contributors_x_icon, href: "https://twitter.com/IYAA_HHHH" },
    contributors_rera_x: { img: contributors_x_icon, href: "https://twitter.com/rerassi" },
    contributors_rera_github: { img: contributors_github_icon, href: "https://github.com/soumt-r" },
    contributors_poposuke_x: { img: contributors_x_icon, href: "https://twitter.com/sig_popo" },
    contributors_kumaguma_x: { img: contributors_x_icon, href: "https://twitter.com/K_kumaguma_A" },
    contributors_riku_x: { img: contributors_x_icon, href: "https://twitter.com/Riku7302" },
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